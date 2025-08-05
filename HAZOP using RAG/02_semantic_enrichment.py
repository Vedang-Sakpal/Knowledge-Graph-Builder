import config
from neo4j import GraphDatabase
import google.generativeai as genai
import json
import os
import fitz
import time
import hashlib
import pickle

# --- Helper Functions ---
def flatten_dict(d, parent_key='', sep='_'):
    """
    Recursively flattens a nested dictionary.
    Example: {'a': 1, 'b': {'c': 2}} becomes {'a': 1, 'b_c': 2}.
    This is useful for setting properties on Neo4j nodes, which don't support nested objects.
    """
    items = []
    for k, v in d.items():
        # Clean up the key by replacing common special characters with underscores.
        sanitized_key = k.replace(' ', '_').replace('/', '_').replace('-', '_').replace('.', '_')
        new_key = parent_key + sep + sanitized_key if parent_key else sanitized_key
        # If the value is a dictionary itself, recurse deeper.
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            # Handle None values as empty strings.
            if v is None:
                items.append((new_key, ''))
            # Keep standard data types as they are.
            elif isinstance(v, (str, int, float, bool)):
                items.append((new_key, v))
            # Convert any other type (like lists) to a string representation.
            else:
                items.append((new_key, str(v)))
    return dict(items)

# --- Main Class ---
class SemanticEnricher:
    """
    This class connects to a Neo4j database, uses an LLM (Gemini) to extract structured
    information from text files, and then "enriches" the graph with this new data.
    It includes caching and API usage limits to be efficient and cost-effective.
    """
    def __init__(self, uri, user, password):
        """
        Initializes the enricher, setting up database and API connections.
        """
        # Initialize the Neo4j database driver.
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # --- Initialize Gemini API ---
        # Configure the API with the key from the config file.
        genai.configure(api_key=config.GEMINI_API_KEY)
        # Set up the specific generative model to use.
        self.model = genai.GenerativeModel(
            model_name=getattr(config, 'GEMINI_MODEL_NAME', 'gemini-1.5-flash'),
            # Configure generation parameters for more predictable output.
            generation_config={
                "temperature": 0.1,  # Lower temperature means less random, more deterministic responses.
                "max_output_tokens": 1500, # Limit the length of the response.
            }
        )
        
        # --- Initialize Caching System ---
        # Caching saves API results to avoid making the same expensive call multiple times.
        self.cache_dir = "api_cache"
        os.makedirs(self.cache_dir, exist_ok=True) # Create the cache directory if it doesn't exist.
        self.api_call_count = 0
        # Set a limit on API calls per run to control costs. Default to 10 if not in config.
        self.max_api_calls = getattr(config, 'MAX_API_CALLS_PER_RUN', 10)

    def close(self):
        """Closes the Neo4j database connection and prints a summary."""
        self.driver.close()
        print(f"Total API calls made in this session: {self.api_call_count}")

    # --- Caching Methods ---
    def _get_cache_key(self, content, prompt_template):
        """Generate a unique MD5 hash for the content and prompt combination to use as a filename."""
        combined = f"{prompt_template}\n{content}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _save_to_cache(self, cache_key, result):
        """Save an API result to a file using pickle."""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)

    def _load_from_cache(self, cache_key):
        """Load an API result from the cache if the file exists."""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None

    # --- File Reading Method ---
    def get_text_from_file(self, file_path):
        """Extracts plain text from PDF, TXT, or MD files."""
        try:
            # Handle PDF files using the fitz library.
            if file_path.lower().endswith('.pdf'):
                doc = fitz.open(file_path)
                text = "".join(page.get_text() for page in doc)
                doc.close()
                return text
            # Handle plain text or markdown files.
            elif file_path.lower().endswith(('.txt', '.md')):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return None
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None

    # --- Core LLM Extraction Method ---
    def extract_info_with_llm(self, context, prompt_template):
        """
        Extracts structured information from text using the Gemini LLM.
        It uses caching to avoid redundant API calls.
        """
        # First, check if we have reached the self-imposed API call limit.
        if self.api_call_count >= self.max_api_calls:
            print(f"API call limit ({self.max_api_calls}) reached. Skipping this extraction.")
            return None

        # Check the cache before making an expensive API call.
        cache_key = self._get_cache_key(context, prompt_template)
        cached_result = self._load_from_cache(cache_key)
        
        if cached_result is not None:
            print("Using cached result instead of making API call.")
            return cached_result

        print(f"Making API call {self.api_call_count + 1}/{self.max_api_calls} to Gemini...")
        
        # Truncate the context if it's too long to save on token costs.
        max_context_length = getattr(config, 'MAX_CONTEXT_LENGTH', 8000)
        if len(context) > max_context_length:
            print(f"Context too long ({len(context)} chars), truncating to {max_context_length} chars")
            context = context[:max_context_length] + "...[truncated]"
        
        # Construct the full prompt for the LLM, clearly stating the required JSON format.
        full_prompt = f"""You are a data extraction expert. Extract information in structured JSON format. Be concise but accurate.

{prompt_template}

---CONTEXT---
{context}

Please provide your response as a valid JSON object only, with no additional text or explanations."""
        
        try:
            # Make the actual API call to the Gemini model.
            response = self.model.generate_content(full_prompt)
            
            # --- Extract JSON from the model's response ---
            # LLMs sometimes wrap JSON in markdown backticks, so we need to clean it up.
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3] # Remove ```json and ```
            elif response_text.startswith('```'):
                response_text = response_text[3:-3] # Remove ``` and ```
            
            # Parse the cleaned text into a Python dictionary.
            extracted_json = json.loads(response_text)
            self.api_call_count += 1
            
            # Save the successful result to the cache for future use.
            self._save_to_cache(cache_key, extracted_json)
            
            print("Successfully extracted information from Gemini API.")
            return extracted_json
            
        except json.JSONDecodeError as e:
            # Handle cases where the LLM response is not valid JSON.
            print(f"JSON decoding error: {e}")
            print(f"Raw response: {response.text}")
            self.api_call_count += 1
            return None
        except Exception as e:
            # Handle other potential API errors.
            print(f"An error occurred during Gemini API call: {e}")
            self.api_call_count += 1 # Count failed calls towards the limit.
            return None

    # --- Batch Processing Method ---
    def batch_process_msds_files(self, msds_dir, process_desc_text, max_files=None):
        """
        Process multiple MSDS files in batches to minimize the number of API calls.
        """
        if not os.path.isdir(msds_dir):
            print(f"MSDS directory not found at {msds_dir}. Skipping MSDS enrichment.")
            return

        # Get a list of all PDF and TXT files in the specified directory.
        msds_files = [f for f in os.listdir(msds_dir) if f.lower().endswith((".txt", ".pdf"))]
        
        # If max_files is set, only process a limited number of files.
        if max_files:
            msds_files = msds_files[:max_files]
            print(f"Limited to processing {max_files} MSDS files to save API calls")

        print(f"\nStarting MSDS enrichment from directory: {msds_dir}")
        print(f"Found {len(msds_files)} MSDS files to process")

        # Process files in batches (e.g., 3 files per API call).
        batch_size = getattr(config, 'MSDS_BATCH_SIZE', 3)
        
        for i in range(0, len(msds_files), batch_size):
            # Stop if the API limit is reached.
            if self.api_call_count >= self.max_api_calls:
                print("API limit reached, stopping MSDS processing")
                break
                
            batch_files = msds_files[i:i + batch_size]
            combined_msds_content = ""
            
            # Combine the text from all files in the current batch into a single string.
            for filename in batch_files:
                file_path = os.path.join(msds_dir, filename)
                msds_text = self.get_text_from_file(file_path)
                if msds_text:
                    # Truncate individual file text to ensure the combined context isn't excessively long.
                    max_individual_length = 2000
                    if len(msds_text) > max_individual_length:
                        msds_text = msds_text[:max_individual_length] + "...[truncated]"
                    combined_msds_content += f"\n\n=== MSDS FILE: {filename} ===\n{msds_text}"

            if combined_msds_content:
                # Create a combined context with both the general process and the batch of MSDS files.
                combined_context = f"GENERAL PROCESS DESCRIPTION:\n{process_desc_text}\n\n---\n\nMSDS BATCH CONTENT:\n{combined_msds_content}"
                
                # A specific prompt designed for extracting chemical data from the batched content.
                batch_msds_prompt = """
                You are an expert chemical safety specialist extracting critical hazard data from one or more Safety Data Sheets (SDS) to support a HAZOP risk assessment.
                From the provided context (which includes a general process description and SDS content), extract the following data for EACH chemical identified in the SDS files.
                
                For each chemical, identify:
                1.  `chemicalName` and `casNumber`.
                2.  `signalWord`: The hazard signal word (e.g., "Danger", "Warning").
                3.  `physicalAndChemicalProperties`: Key physical data relevant to containment and fire/explosion hazards.
                4.  `stabilityAndReactivity`: Information on reactivity hazards.
                5.  `toxicologicalInformation`: Key toxicity data.
                6.  `identifiedVessel`: Use the "GENERAL PROCESS DESCRIPTION" context to infer the name of the vessel or equipment where this chemical is primarily used or stored.
                
                Provide your response as a single, valid JSON object with a key "chemical_data" containing a list of objects. Ensure all values include units where applicable. If a value is not found, use `null`.
                
                Example Format:
                {
                  "chemical_data": [
                    {
                      "chemicalName": "Methanol",
                      "casNumber": "67-56-1",
                      "signalWord": "Danger",
                      "identifiedVessel": "V-101",
                      "physicalAndChemicalProperties": {
                        "physicalState": "Liquid",
                        "flashPoint": "11 C",
                        "autoignitionTemperature": "464 C",
                        "boilingPoint": "64.7 C",
                        "vaporPressure": "128 hPa @ 20 C",
                        "upperExplosiveLimit": "36 %",
                        "lowerExplosiveLimit": "6 %"
                      },
                      "stabilityAndReactivity": {
                        "reactivityHazards": "May react violently with strong oxidizing agents.",
                        "conditionsToAvoid": "Heat, flames, sparks, and other ignition sources.",
                        "incompatibleMaterials": "Strong acids, strong bases, oxidizing agents."
                      },
                      "toxicologicalInformation": {
                        "routesOfExposure": "Inhalation, Skin, Eyes, Ingestion.",
                        "healthEffects": "Toxic if swallowed, in contact with skin or if inhaled. Causes damage to organs (optic nerve)."
                      }
                    }
                  ]
                }"""
                
                extracted_batch_data = self.extract_info_with_llm(combined_context, batch_msds_prompt)
                if extracted_batch_data:
                    # If data is successfully extracted, add it to the graph.
                    self.enrich_graph(extracted_batch_data)
                    print(f"Processed batch of {len(batch_files)} files")
                
                # Wait for a few seconds between batch calls to be respectful of API rate limits.
                time.sleep(5)

    # --- Graph Update Method ---
    def enrich_graph(self, extracted_data):
        """
        Takes the structured JSON from the LLM and writes it to the Neo4j database.
        This version uses 'Id' as the primary key for Equipment nodes.
        """
        print("Enriching the Neo4j graph with extracted data...")
        with self.driver.session() as session:
            # --- Handle Equipment and Stream Data (from process description) ---
            if 'equipment' in extracted_data:
                for item in extracted_data.get('equipment', []):
                    # <<< CHANGE: Get 'equipmentId' from the JSON
                    equipment_id = item.get('equipmentId')
                    if equipment_id:
                        params = flatten_dict(item)
                        # <<< CHANGE: Ensure the 'Id' property is set for the query
                        params['id'] = equipment_id
                        # <<< CHANGE: MERGE on the 'Id' property
                        query = "MERGE (n:Equipment {id: $id}) SET n += $params"
                        session.run(query, id=equipment_id, params=params)
                        print(f"Enriched Equipment '{equipment_id}' with parameters.")

            if 'streams' in extracted_data:
                 for stream in extracted_data.get('streams', []):
                    # <<< CHANGE: Get source and destination by 'Id'
                    source_id = stream.get('sourceEquipmentId')
                    destination_id = stream.get('destinationEquipmentId')
                    if source_id and destination_id:
                        rel_props = flatten_dict(stream)
                        # <<< CHANGE: MATCH source and destination on their 'Id' property
                        query = """
                        MATCH (src:Equipment {id: $source_id})
                        MATCH (dest:Equipment {id: $destination_id})
                        MERGE (src)-[r:FLOWS_TO]->(dest)
                        SET r = $props
                        """
                        session.run(query, source_id=source_id, destination_id=destination_id, props=rel_props)
                        print(f"Created/Updated stream from '{source_id}' to '{destination_id}'.")

            # --- Handle Chemical Data (from MSDS batch processing) ---
            if 'chemical_data' in extracted_data:
                for chem in extracted_data.get('chemical_data', []):
                    name = chem.get('chemicalName')
                    # This key comes from the MSDS prompt ('identifiedVessel')
                    vessel_id = chem.get('identifiedVessel')

                    if name:
                        all_props = flatten_dict(chem)
                        all_props['name'] = name # Chemical nodes will still use 'name'

                        session.run("MERGE (c:Chemical {name: $name}) SET c = $all_props", name=name, all_props=all_props)
                        print(f"Added/Updated chemical: {name}")

                        if vessel_id:
                            # <<< CHANGE: Match the vessel (Equipment) on its 'Id' property
                            session.run("""
                                MATCH (v:Equipment {id: $vessel_id})
                                MATCH (c:Chemical {name: $chem_name})
                                MERGE (v)-[:CONTAINS]->(c)
                            """, vessel_id=vessel_id, chem_name=name)
                            print(f"Linked '{name}' to vessel '{vessel_id}'.")

def main():
    """Main execution function to run the semantic enrichment process."""
    enricher = SemanticEnricher(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
    
    # --- Step 1: Process the general process description file ---
    process_desc_text = enricher.get_text_from_file(config.PROCESS_DESC_PATH)
    if process_desc_text:
        # <<< CHANGE: The prompt is updated to use 'Id' fields for equipment.
        process_prompt = """
        You are a senior process design and safety engineer creating a detailed digital model of a process for a comprehensive HAZOP study. From the provided text, perform two tasks:
        1.  Extract data for all major tagged **equipment** (e.g., 'V-101', 'P-201').
        2.  Extract data for all **process streams** or **pipes** that connect the equipment, defining the material flow and its properties.

        The final output must be a single, valid JSON object with two top-level keys: "equipment" and "streams".

        For the **"equipment"** list, include:
        - `equipmentId`: The unique tag for the equipment (e.g., "RX-101").
        - `equipmentType`.
        - `operatingParameters` (temperature, pressure).
        - `designLimits` (design temperature, design pressure).
        - `materialOfConstruction`.

        For the **"streams"** list, include:
        - `streamName`: The name or description of the pipe/line.
        - `sourceEquipmentId`: The tag Id where the flow originates.
        - `destinationEquipmentId`: The tag Id where the flow terminates.
        - `transportedMaterial`: The name of the chemical or mixture flowing in the pipe.
        - `properties`: The conditions within the pipe (temperature, pressure, flowRate).

        Ensure all values include units. If a value is not found, use `null`.

        Example Format:
        {
          "equipment": [
            {
              "equipmentId": "V-101",
              "equipmentType": "Feed Drum",
              "operatingParameters": { "temperature": "50 C", "pressure": "5 barg" },
              "designLimits": { "designTemperature": "100 C", "designPressure": "10 barg" },
              "materialOfConstruction": "Carbon Steel"
            }
          ],
          "streams": [
            {
              "streamName": "Pump P-101 Suction Line",
              "sourceEquipmentId": "V-101",
              "destinationEquipmentId": "P-101",
              "transportedMaterial": "Crude Benzene",
              "properties": { "temperature": "50 C", "pressure": "5 barg" }
            }
          ]
        }
        """
        extracted_process_data = enricher.extract_info_with_llm(process_desc_text, process_prompt)
        if extracted_process_data:
            enricher.enrich_graph(extracted_process_data)

    # --- Step 2: Process MSDS files in batches ---
    max_msds_files = getattr(config, 'MAX_MSDS_FILES', 5) 
    enricher.batch_process_msds_files(config.MSDS_DIRECTORY_PATH, process_desc_text, max_msds_files)
    
    # --- Step 3: Clean up ---
    enricher.close()
    print("\nPhase 2: Semantic Enrichment complete.")
# Standard Python entry point. The code inside this block runs only when
# the script is executed directly (not when imported as a module).
if __name__ == "__main__":
    main()