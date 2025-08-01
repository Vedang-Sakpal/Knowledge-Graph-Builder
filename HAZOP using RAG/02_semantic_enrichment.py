import config
from neo4j import GraphDatabase
import google.generativeai as genai
import json
import os
import fitz
import time
import hashlib
import pickle

def flatten_dict(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        sanitized_key = k.replace(' ', '_').replace('/', '_').replace('-', '_').replace('.', '_')
        new_key = parent_key + sep + sanitized_key if parent_key else sanitized_key
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            if v is None:
                items.append((new_key, ''))
            elif isinstance(v, (str, int, float, bool)):
                 items.append((new_key, v))
            else:
                 items.append((new_key, str(v)))
    return dict(items)

class SemanticEnricher:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        # Initialize Gemini API
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=getattr(config, 'GEMINI_MODEL_NAME', 'gemini-1.5-flash'),
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 1500,
            }
        )
        
        # Initialize caching system
        self.cache_dir = "api_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        self.api_call_count = 0
        self.max_api_calls = getattr(config, 'MAX_API_CALLS_PER_RUN', 10)  # Default limit

    def close(self):
        self.driver.close()
        print(f"Total API calls made in this session: {self.api_call_count}")

    def _get_cache_key(self, content, prompt_template):
        """Generate a unique cache key for the content and prompt combination"""
        combined = f"{prompt_template}\n{content}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _save_to_cache(self, cache_key, result):
        """Save API result to cache"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)

    def _load_from_cache(self, cache_key):
        """Load API result from cache if it exists"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None

    def get_text_from_file(self, file_path):
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
                return None
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None

    def extract_info_with_llm(self, context, prompt_template):
        # Check API call limit
        if self.api_call_count >= self.max_api_calls:
            print(f"API call limit ({self.max_api_calls}) reached. Skipping this extraction.")
            return None

        # Check cache first
        cache_key = self._get_cache_key(context, prompt_template)
        cached_result = self._load_from_cache(cache_key)
        
        if cached_result is not None:
            print("Using cached result instead of making API call.")
            return cached_result

        print(f"Making API call {self.api_call_count + 1}/{self.max_api_calls} to Gemini...")
        
        # Truncate context if too long to save tokens
        max_context_length = getattr(config, 'MAX_CONTEXT_LENGTH', 8000)  # Default 8k chars
        if len(context) > max_context_length:
            print(f"Context too long ({len(context)} chars), truncating to {max_context_length} chars")
            context = context[:max_context_length] + "...[truncated]"
        
        full_prompt = f"""You are a data extraction expert. Extract information in structured JSON format. Be concise but accurate.

{prompt_template}

---CONTEXT---
{context}

Please provide your response as a valid JSON object only, with no additional text or explanations."""
        
        try:
            response = self.model.generate_content(full_prompt)
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Try to find JSON in the response
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]  # Remove ```json and ```
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]  # Remove ``` and ```
            
            extracted_json = json.loads(response_text)
            self.api_call_count += 1
            
            # Save to cache
            self._save_to_cache(cache_key, extracted_json)
            
            print("Successfully extracted information from Gemini API.")
            return extracted_json
            
        except json.JSONDecodeError as e:
            print(f"JSON decoding error: {e}")
            print(f"Raw response: {response.text}")
            self.api_call_count += 1
            return None
        except Exception as e:
            print(f"An error occurred during Gemini API call: {e}")
            self.api_call_count += 1  # Count failed calls too
            return None

    def batch_process_msds_files(self, msds_dir, process_desc_text, max_files=None):
        """Process MSDS files in batches to minimize API calls"""
        if not os.path.isdir(msds_dir):
            print(f"MSDS directory not found at {msds_dir}. Skipping MSDS enrichment.")
            return

        msds_files = [f for f in os.listdir(msds_dir) if f.lower().endswith((".txt", ".pdf"))]
        
        if max_files:
            msds_files = msds_files[:max_files]
            print(f"Limited to processing {max_files} MSDS files to save API calls")

        print(f"\nStarting MSDS enrichment from directory: {msds_dir}")
        print(f"Found {len(msds_files)} MSDS files to process")

        # Process files in batches
        batch_size = getattr(config, 'MSDS_BATCH_SIZE', 3)  # Process multiple files per API call
        
        for i in range(0, len(msds_files), batch_size):
            if self.api_call_count >= self.max_api_calls:
                print("API limit reached, stopping MSDS processing")
                break
                
            batch_files = msds_files[i:i + batch_size]
            combined_msds_content = ""
            
            for filename in batch_files:
                file_path = os.path.join(msds_dir, filename)
                msds_text = self.get_text_from_file(file_path)
                if msds_text:
                    # Truncate individual MSDS if too long
                    max_individual_length = 2000  # Shorter per file to fit batch
                    if len(msds_text) > max_individual_length:
                        msds_text = msds_text[:max_individual_length] + "...[truncated]"
                    combined_msds_content += f"\n\n=== MSDS FILE: {filename} ===\n{msds_text}"

            if combined_msds_content:
                combined_context = f"GENERAL PROCESS DESCRIPTION:\n{process_desc_text}\n\n---\n\nMSDS BATCH CONTENT:\n{combined_msds_content}"
                
                batch_msds_prompt = """
                From the combined context (process description + multiple MSDS files), extract chemical data for ALL chemicals found.
                For each chemical, identify: chemical name, properties, and the vessel/equipment where it's stored/used.
                Format as JSON with "chemical_data" key containing a list of chemical objects.
                Example: {"chemical_data": [{"chemical_name": "Methanol", "stored_in_vessel_name": "V-001", "properties": {"flashPoint": "11 C"}}]}
                """
                
                extracted_batch_data = self.extract_info_with_llm(combined_context, batch_msds_prompt)
                if extracted_batch_data:
                    self.enrich_graph(extracted_batch_data)
                    print(f"Processed batch of {len(batch_files)} files")
                
                # Longer sleep between batches to respect rate limits
                time.sleep(5)

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
                        session.run("MERGE (c:Chemical {name: $name}) SET c = $all_props", name=name, all_props=all_props)
                        print(f"Added/Updated chemical: {name}")
                        if vessel_name:
                            session.run("MATCH (v {name: $vessel_name}), (c:Chemical {name: $chem_name}) MERGE (v)-[:CONTAINS]->(c)", vessel_name=vessel_name, chem_name=name)
                            print(f"Linked '{name}' to vessel '{vessel_name}'.")

def main():
    enricher = SemanticEnricher(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
    
    # Process description (single API call)
    process_desc_text = enricher.get_text_from_file(config.PROCESS_DESC_PATH)
    if process_desc_text:
        process_prompt = """
        Extract operating parameters for major equipment from this process description.
        Focus on equipment with names like 'V-001', 'P-203', etc.
        Extract key parameters: operatingPressure, operatingTemperature, designPressure.
        Format: {"equipment_parameters": [{"name": "V-002", "parameters": {"operatingPressure": "10 barg"}}]}
        """
        extracted_process_data = enricher.extract_info_with_llm(process_desc_text, process_prompt)
        if extracted_process_data:
            enricher.enrich_graph(extracted_process_data)

    # Process MSDS files with limits
    max_msds_files = getattr(config, 'MAX_MSDS_FILES', 5)  # Limit number of MSDS files
    enricher.batch_process_msds_files(config.MSDS_DIRECTORY_PATH, process_desc_text, max_msds_files)
    
    enricher.close()
    print("\nPhase 2: Semantic Enrichment complete.")

if __name__ == "__main__":
    main()