# UPDATED: This script now uses the OpenAI API.

import config
from neo4j import GraphDatabase
import openai
import json
import os
import fitz  # PyMuPDF
import time

def flatten_dict(d, parent_key='', sep='_'):
    """
    Recursively flattens a nested dictionary.
    Example: {'a': {'b': 1}} becomes {'a_b': 1}
    """
    items = []
    for k, v in d.items():
        # Sanitize the key to be a valid Cypher identifier
        sanitized_key = k.replace(' ', '_').replace('/', '_').replace('-', '_').replace('.', '_')
        new_key = parent_key + sep + sanitized_key if parent_key else sanitized_key
        
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            # Ensure the value is a primitive type, converting to string if necessary
            if v is None:
                items.append((new_key, ''))
            elif isinstance(v, (str, int, float, bool)):
                 items.append((new_key, v))
            else:
                 items.append((new_key, str(v)))

    return dict(items)

class SemanticEnricher:
    def __init__(self, uri, user, password, api_key):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        openai.api_key = api_key

    def close(self):
        self.driver.close()

    def get_text_from_file(self, file_path):
        """Reads content from a file, supporting both .txt and .pdf."""
        try:
            if file_path.lower().endswith('.pdf'):
                doc = fitz.open(file_path)
                text = "".join(page.get_text() for page in doc)
                doc.close()
                return text
            elif file_path.lower().endswith(('.txt', '.md')):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                print(f"Warning: Unsupported file type for {file_path}. Skipping.")
                return None
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
            return None
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None

    def extract_info_with_llm(self, context, prompt_template):
        print("Contacting OpenAI API for information extraction...")
        full_prompt = f"{prompt_template}\n\n---CONTEXT---\n{context}"
        try:
            response = openai.chat.completions.create(
                model=config.LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a data extraction expert. Your task is to read the provided text and extract information in a structured JSON format. Do not add any explanatory text outside of the JSON object."},
                    {"role": "user", "content": full_prompt}
                ],
                response_format={"type": "json_object"}
            )
            extracted_json = json.loads(response.choices[0].message.content)
            print("Successfully extracted information from OpenAI API.")
            return extracted_json
        except Exception as e:
            print(f"An error occurred during OpenAI API call: {e}")
            return None

    def enrich_graph(self, extracted_data):
        print("Enriching the Neo4j graph with extracted data...")
        with self.driver.session() as session:
            if 'equipment_parameters' in extracted_data:
                for item in extracted_data.get('equipment_parameters', []):
                    name = item.get('name')
                    params = item.get('parameters', {})
                    if name:
                        query = "MATCH (n {name: $name}) SET n += $params"
                        session.run(query, name=name, params=params)
                        print(f"Enriched component '{name}' with parameters.")

            if 'chemical_data' in extracted_data:
                for chem in extracted_data.get('chemical_data', []):
                    name = chem.get('chemical_name')
                    properties = chem.get('properties', {})
                    vessel_name = chem.get('stored_in_vessel_name')
                    if name:
                        all_props = {'name': name}
                        flattened_properties = flatten_dict(properties)
                        all_props.update(flattened_properties)

                        session.run("""
                            MERGE (c:Chemical {name: $name})
                            SET c = $all_props
                        """, name=name, all_props=all_props)
                        print(f"Added/Updated chemical: {name}")
                        if vessel_name:
                            session.run("""
                                MATCH (v {name: $vessel_name})
                                MATCH (c:Chemical {name: $chem_name})
                                MERGE (v)-[:CONTAINS]->(c)
                            """, vessel_name=vessel_name, chem_name=name)
                            print(f"Linked '{name}' to vessel '{vessel_name}'.")

def main():
    enricher = SemanticEnricher(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD, config.LLM_API_KEY)

    process_desc_text = enricher.get_text_from_file(config.PROCESS_DESC_PATH)
    if process_desc_text:
        process_prompt = """
        From the process description text provided, extract the operating parameters for each piece of major equipment.
        Identify equipment by its name (e.g., 'V-001', 'P-203').
        For each piece of equipment, extract parameters like 'operatingPressure', 'operatingTemperature', and 'designPressure'.
        Format the output as a single valid JSON object with a single key "equipment_parameters", which is a list of objects. Do not add any explanatory text.
        Example JSON format:
        {"equipment_parameters": [{"name": "V-002", "parameters": {"operatingPressure": "10 barg", "operatingTemperature": "150 C"}}]}
        """
        extracted_process_data = enricher.extract_info_with_llm(process_desc_text, process_prompt)
        if extracted_process_data:
            enricher.enrich_graph(extracted_process_data)

    msds_dir = config.MSDS_DIRECTORY_PATH
    if os.path.isdir(msds_dir):
        print(f"\nStarting MSDS enrichment from directory: {msds_dir}")
        for filename in os.listdir(msds_dir):
            if filename.lower().endswith((".txt", ".pdf")):
                print(f"\n--- Processing MSDS file: {filename} ---")
                file_path = os.path.join(msds_dir, filename)
                msds_text = enricher.get_text_from_file(file_path)
                
                if msds_text:
                    combined_context = f"GENERAL PROCESS DESCRIPTION:\n{process_desc_text}\n\n---\n\nSPECIFIC MSDS CONTENT:\n{msds_text}"
                    msds_prompt = """
                    From the combined context provided (which includes a general process description and a specific MSDS), perform two tasks:
                    1. From the MSDS content, extract key safety and physical properties for the chemical.
                    2. From the combined context, deduce the name of the primary vessel or equipment (e.g., 'V-001', 'Tank 1') where this specific chemical is stored or used.
                    Format the output as a single valid JSON object with a single key "chemical_data", which is a list of objects. Do not add any explanatory text.
                    Each object must have "chemical_name", "stored_in_vessel_name", and a "properties" object.
                    Example JSON format:
                    {"chemical_data": [{"chemical_name": "Methanol", "stored_in_vessel_name": "V-001", "properties": {"flashPoint": "11 C", "toxicity": "Toxic if swallowed"}}]}
                    """
                    extracted_msds_data = enricher.extract_info_with_llm(combined_context, msds_prompt)
                    if extracted_msds_data:
                        enricher.enrich_graph(extracted_msds_data)
                    time.sleep(2)
    else:
        print(f"MSDS directory not found at {msds_dir}. Skipping MSDS enrichment.")

    enricher.close()
    print("\nPhase 2: Semantic Enrichment complete.")

if __name__ == "__main__":
    main()