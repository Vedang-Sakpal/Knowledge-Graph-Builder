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

    # --- Synonym Enrichment and Mapping ---
    def enrich_chemicals_with_synonyms(self):
        """
        Finds chemicals in the DB without a 'synonyms' property, uses an LLM
        to find synonyms, and updates the node.
        """
        print("\n--- Starting Chemical Synonym Enrichment ---")
        with self.driver.session() as session:
            # Find chemicals that haven't been enriched with synonyms yet.
            result = session.run("MATCH (c:Chemical) WHERE c.synonyms IS NULL RETURN c.name AS name")
            chemicals_to_enrich = [record["name"] for record in result]

            if not chemicals_to_enrich:
                print("All chemical nodes are already enriched with synonyms.")
                return

            print(f"Found {len(chemicals_to_enrich)} chemicals to enrich with synonyms.")

            # --- IMPROVED PROMPT 1: Asks for commercial/brand names ---
            synonym_prompt_template = """
            For the substance identified as "{chemical_name}", provide a list of its common names, synonyms, formulas, and any major commercial or brand names.
            Include the original name in the list.
            Return a single JSON object with a key "synonyms" containing a list of strings.
            Example: For "Whey Permeate", return {{"synonyms": ["Whey Permeate", "deproteinized whey", "dairy solids", "wheyco permeate"]}}.
            """

            for name in chemicals_to_enrich:
                if self.api_call_count >= self.max_api_calls:
                    print("API limit reached, stopping synonym enrichment.")
                    break

                print(f"Getting synonyms for: {name}")
                # Use the template to create the final prompt for each chemical
                final_prompt = synonym_prompt_template.format(chemical_name=name)
                response = self.extract_info_with_llm(name, final_prompt)

                try:
                    if response and 'synonyms' in response and isinstance(response['synonyms'], list):
                        synonyms = response['synonyms']
                        # Ensure all synonyms are strings and lowercase for consistent matching
                        synonyms_lower = list(set([str(s).lower() for s in synonyms]))

                        # Add the original name to the list if not present, in lowercase
                        if name.lower() not in synonyms_lower:
                            synonyms_lower.append(name.lower())

                        session.run(
                            "MATCH (c:Chemical {name: $name}) SET c.synonyms = $synonyms",
                            name=name,
                            synonyms=synonyms_lower
                        )
                        print(f"Successfully added synonyms for '{name}': {synonyms_lower}")
                    else:
                        print(f"Could not retrieve or parse synonyms for '{name}'. Response received: {response}")

                except KeyError:
                    # This block will catch the specific error and provide better debug info
                    print(f"KeyError while processing '{name}'. The AI response did not contain the expected 'synonyms' key.")
                    print(f"Raw response dictionary keys: {response.keys() if isinstance(response, dict) else 'Not a dict'}")
                    print(f"Full response: {response}")

                time.sleep(2) # Rate limiting

    def get_synonym_to_canonical_map(self):
        """
        Creates a dictionary mapping every synonym to its canonical chemical name.
        """
        print("\nBuilding synonym map from database...")
        with self.driver.session() as session:
            # UNWIND expands the list of synonyms into individual rows
            result = session.run("""
                MATCH (c:Chemical) WHERE c.synonyms IS NOT NULL
                UNWIND c.synonyms AS synonym
                RETURN synonym, c.name AS canonicalName
            """)
            # The map uses lowercase synonyms as keys for case-insensitive matching
            synonym_map = {record["synonym"].lower(): record["canonicalName"] for record in result}
            print(f"Built map with {len(synonym_map)} synonym entries.")
            return synonym_map

    # --- MSDS Processing Method ---
    def process_msds_files(self, msds_dir, synonym_map, max_files=None):
        """
        Process MSDS files, using the synonym map to match them to canonical chemicals.
        """
        if not os.path.isdir(msds_dir):
            print(f"MSDS directory not found at {msds_dir}. Skipping MSDS enrichment.")
            return

        msds_files = [f for f in os.listdir(msds_dir) if f.lower().endswith((".txt", ".pdf"))]

        if max_files:
            msds_files = msds_files[:max_files]
            print(f"Limited to processing a maximum of {max_files} MSDS files.")

        print(f"\n--- Starting MSDS Processing using Synonym Map ---")
        print(f"Found {len(msds_files)} MSDS files to process.")

        # --- IMPROVED PROMPT 2: Guides the AI to find the generic name ---
        msds_prompt = """
        You are an expert chemical safety specialist extracting critical hazard data from a Safety Data Sheet (SDS) or product specification sheet.
        From the provided content, extract the following data for the substance.

        Identify:
        1.  `chemicalName`: The most common or generic chemical/substance name. If a brand name is present (e.g., 'wheyco Permeate'), extract the generic part (e.g., 'Whey Permeate'). Also identify the `casNumber` if available.
        2.  `signalWord`: The hazard signal word (e.g., "Danger", "Warning").
        3.  `physicalAndChemicalProperties`: Key physical data.
        4.  `stabilityAndReactivity`: Information on reactivity hazards.
        5.  `toxicologicalInformation`: Key toxicity data.

        Provide your response as a single, valid JSON object.
        """

        for filename in msds_files:
            if self.api_call_count >= self.max_api_calls:
                print("API limit reached, stopping further MSDS processing.")
                break

            file_path = os.path.join(msds_dir, filename)
            msds_text = self.get_text_from_file(file_path)

            if not msds_text:
                continue

            extracted_data = self.extract_info_with_llm(msds_text, msds_prompt)

            if extracted_data and isinstance(extracted_data, dict):
                chem_name_from_msds = extracted_data.get('chemicalName')
                if chem_name_from_msds:
                    # Check if the extracted name (or its lowercase version) is in our synonym map
                    canonical_name = synonym_map.get(chem_name_from_msds.lower())

                    if canonical_name:
                        print(f"Match found: '{chem_name_from_msds}' from '{filename}' maps to canonical chemical '{canonical_name}'. Enriching...")
                        self.enrich_graph_with_chemical_data(extracted_data, canonical_name)
                    else:
                        print(f"Skipping: Chemical '{chem_name_from_msds}' from '{filename}' does not match any known chemical in the database.")
                else:
                    print(f"Skipping '{filename}': Could not extract a chemical name from the document.")

            time.sleep(3) # Be respectful of API rate limits.

    # --- Graph Update Method ---
    def enrich_graph_with_chemical_data(self, chemical_data, canonical_name):
        """
        Takes the structured JSON for a single chemical and updates its canonical node in Neo4j.
        """
        print(f"Enriching the Neo4j graph for canonical chemical: {canonical_name}...")
        with self.driver.session() as session:
            # Flatten the nested dictionary for Neo4j properties.
            params = flatten_dict(chemical_data)

            # This query finds the canonical chemical by its primary name and adds/updates its properties.
            # Using 'SET n += $params' ensures we only add/update data without overwriting the node
            # and its existing relationships.
            query = "MERGE (n:Chemical {name: $canonical_name}) SET n += $params"
            session.run(query, canonical_name=canonical_name, params=params)
            print(f"Enriched Chemical Node '{canonical_name}' with new properties.")


def main():
    """Main execution function to run the semantic enrichment process."""
    enricher = SemanticEnricher(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)

    # --- Step 1: Pre-process the database to ensure all chemicals have synonym lists ---
    enricher.enrich_chemicals_with_synonyms()

    # --- Step 2: Build a map from any synonym to its canonical chemical name ---
    synonym_map = enricher.get_synonym_to_canonical_map()

    # --- Step 3: Process MSDS files using the synonym map for matching ---
    if synonym_map:
        max_msds_files = getattr(config, 'MAX_MSDS_FILES', 10)
        enricher.process_msds_files(config.MSDS_DIRECTORY_PATH, synonym_map, max_msds_files)
    else:
        print("Could not build a synonym map. Skipping MSDS processing.")

    # --- Step 4: Clean up ---
    enricher.close()
    print("\nPhase 2: Semantic Enrichment complete.")

# Standard Python entry point.
if __name__ == "__main__":
    main()