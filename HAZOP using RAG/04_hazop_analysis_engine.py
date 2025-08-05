# UPDATED: Optimized to minimize API calls using Gemini API and to write results back to Neo4j.

import config
from neo4j import GraphDatabase
import google.generativeai as genai
import json
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from tqdm import tqdm
import time
import re
import hashlib
import pickle
import os
from collections import Counter

class DeviationGenerator:
    """
    Generates a list of potential HAZOP deviations (e.g., "More Flow", "No Pressure")
    by combining process parameters with standard HAZOP guidewords from a CSV file.
    """
    def __init__(self, csv_path):
        """
        Initializes the generator by loading the parameter-guideword mapping from a CSV.
        """
        print("Initializing Deviation Generator...")
        # Load the mapping from the provided CSV file path.
        self.param_guideword_map = self._load_param_guideword_map(csv_path)
        print("Deviation Generator initialized successfully.")

    def _load_param_guideword_map(self, csv_path):
        """
        Reads the specified CSV file and creates a dictionary mapping each parameter
        to a list of its applicable guidewords.
        """
        try:
            # Read the CSV, skipping the first row (header=1) and filling empty cells.
            df = pd.read_csv(csv_path, header=1).fillna('')
            # The first column is assumed to contain the parameters.
            param_col_name = df.columns[0]
            df.rename(columns={param_col_name: 'Parameter'}, inplace=True)
            # All other columns are guidewords.
            guideword_cols = df.columns[1:]
            df = df.set_index('Parameter')
            param_map = {}
            # Iterate over each parameter (row) in the DataFrame.
            for param, row in df.iterrows():
                param_clean = str(param).strip()
                if param_clean:
                    # A guideword applies if the cell contains a '✔'.
                    applicable_guidewords = [gw.strip() for gw in guideword_cols if '✔' in str(row[gw])]
                    param_map[param_clean] = applicable_guidewords
            print(f"Loaded {len(param_map)} parameters from CSV.")
            return param_map
        except Exception as e:
            print(f"Error loading or parsing {csv_path}: {e}")
            return {}

    def generate_deviations_for_node(self, node_id, max_deviations=None):
        """
        Generates all possible deviations for a given node.
        An optional limit can be set to reduce processing for testing.
        """
        deviations = []
        # Create all combinations of parameters and their applicable guidewords.
        for param, guidewords in self.param_guideword_map.items():
            for guideword in guidewords:
                # Create a safe, unique ID for the deviation.
                dev_id_safe = f"{node_id}-{guideword.replace(' ','')}-{param.replace(' ','')}"
                deviations.append({
                    "deviationID": dev_id_safe,
                    "description": f"{guideword} {param}",
                    "guideword": guideword, "parameter": param, "nodeID": node_id
                })
                
                # If a maximum number of deviations is set, stop when it's reached.
                if max_deviations and len(deviations) >= max_deviations:
                    print(f"Limited deviations to {max_deviations} for node {node_id}")
                    return deviations
                    
        return deviations

class RAGContextBuilder:
    """
    Builds and manages a Retrieval-Augmented Generation (RAG) system.
    This system finds relevant historical data (causes, consequences, safeguards)
    to provide better context to the AI for its analysis.
    """
    def __init__(self):
        """
        Initializes the RAG system by loading data, creating embeddings, and building search indexes.
        """
        print("Initializing RAG Context Builder...")
        # Load a pre-trained model to convert text into numerical embeddings.
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        # Load historical data for causes, consequences, and safeguards from CSVs.
        self.dfs = {
            "causes": pd.read_csv(config.CAUSES_CSV_PATH).dropna(how='all').stack().reset_index(drop=True).to_frame('description'),
            "consequences": pd.read_csv(config.CONSEQUENCES_CSV_PATH).dropna(how='all').stack().reset_index(drop=True).to_frame('description'),
            "safeguards": pd.read_csv(config.SAFEGUARDS_CSV_PATH).dropna(how='all').stack().reset_index(drop=True).to_frame('description')
        }
        # Encode all the text descriptions into numerical embeddings.
        self.embeddings = {k: self.model.encode(v['description'].tolist()) for k, v in self.dfs.items()}
        # Create a FAISS index for each category for fast similarity searching.
        self.indexes = {k: self._create_faiss_index(v) for k, v in self.embeddings.items()}
        print("RAG Context Builder initialized.")

    def _create_faiss_index(self, embeddings):
        """
        Creates a FAISS index from a set of embeddings.
        """
        # Create a flat L2 (Euclidean distance) index.
        index = faiss.IndexFlatL2(embeddings.shape[1])
        # Add the embeddings to the index.
        index.add(np.array(embeddings, dtype=np.float32))
        return index

    def search(self, query, k=2):
        """
        Searches the indexes for the top 'k' most similar items to the query text.
        k=2 is used to keep the context provided to the AI concise and save tokens.
        """
        # Convert the text query into an embedding.
        query_embedding = self.model.encode([query])
        results = {}
        # Search in each index (causes, consequences, safeguards).
        for key, index in self.indexes.items():
            # Perform the search.
            _, indices = index.search(np.array(query_embedding, dtype=np.float32), k)
            # Retrieve the original text descriptions for the top results.
            results[key] = self.dfs[key].iloc[indices[0]]['description'].tolist()
        return results

class LLMConfidenceCalculator:
    """
    Real methods for calculating LLM confidence levels instead of random numbers
    """
    
    def __init__(self):
        # Keywords that typically indicate uncertainty
        self.uncertainty_keywords = [
            'might', 'could', 'may', 'possibly', 'potentially', 'likely', 
            'probably', 'perhaps', 'maybe', 'uncertain', 'unclear', 
            'approximate', 'estimated', 'roughly', 'about', 'around'
        ]
        
        # Keywords that indicate high confidence
        self.confidence_keywords = [
            'will', 'must', 'always', 'never', 'definitely', 'certainly',
            'clearly', 'obviously', 'undoubtedly', 'absolutely', 'precisely',
            'exactly', 'specifically', 'immediately', 'directly'
        ]

    def calculate_linguistic_confidence(self, text):
        """
        Method 1: Analyze the language used to estimate confidence
        """
        if not text or not isinstance(text, str):
            return 0.5  # Default neutral confidence
            
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        uncertainty_count = sum(1 for word in words if word in self.uncertainty_keywords)
        confidence_count = sum(1 for word in words if word in self.confidence_keywords)
        
        total_words = len(words)
        if total_words == 0:
            return 0.5
            
        uncertainty_penalty = uncertainty_count / total_words
        confidence_boost = confidence_count / total_words
        
        base_confidence = 0.7
        confidence = base_confidence + confidence_boost - (uncertainty_penalty * 2)
        
        return max(0.3, min(0.95, confidence))

    def calculate_combined_confidence(self, text, rag_context=None):
        """
        Method 5: Combined approach using multiple indicators
        """
        ling_conf = self.calculate_linguistic_confidence(text)
        
        # In a real scenario, you would calculate and weight multiple confidence scores.
        # For this implementation, we will primarily use linguistic confidence.
        return ling_conf


class AnalysisEngine:
    """
    The main engine that orchestrates the entire HAZOP analysis process.
    It connects to the database, calls the Gemini API, and manages the workflow.
    """
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        # Configure the Gemini API with key and generation settings (low temperature for deterministic output).
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=getattr(config, 'GEMINI_MODEL_NAME', 'gemini-1.5-flash'),
            generation_config={
                "temperature": 0.1,  # Low temperature for more predictable, less "creative" responses.
                "max_output_tokens": 8000,
            }
        )
        # Initialize the helper classes.
        self.rag_builder = RAGContextBuilder()
        self.deviation_generator = DeviationGenerator(config.PARAMETER_GUIDEWORD_CSV_PATH)
        
        # --- Caching and API Call Management ---
        self.cache_dir = "hazop_cache"  # Directory to store cached results.
        os.makedirs(self.cache_dir, exist_ok=True)
        self.api_call_count = 0
        self.max_api_calls = getattr(config, 'MAX_HAZOP_API_CALLS', 20)  # Safety limit to prevent high costs.
        self.processed_nodes = 0

    def close(self):
        """
        Closes the database connection and prints summary statistics.
        """
        self.driver.close()
        print(f"Total HAZOP API calls made: {self.api_call_count}")
        print(f"Processed {self.processed_nodes} nodes")

    def _get_cache_key(self, content):
        """
        Generates a unique MD5 hash from a string to use as a cache filename.
        """
        return hashlib.md5(content.encode()).hexdigest()

    def _save_to_cache(self, cache_key, result):
        """
        Saves a result to a file using pickle for later retrieval.
        """
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)

    def _load_from_cache(self, cache_key):
        """
        Loads a result from the cache if the file exists.
        """
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None

    def get_hazop_nodes(self, max_nodes=None):
        """
        Fetches HAZOP nodes from the Neo4j database.
        An optional limit can be applied to conserve API calls during testing.
        """
        with self.driver.session() as session:
            # Cypher query to get all nodes with the label :HAZOPNode.
            nodes = [r.data() for r in session.run("MATCH (n:HAZOPNode) RETURN n.nodeID AS nodeID, n.description AS description")]
            
            if max_nodes and len(nodes) > max_nodes:
                print(f"Limiting analysis to {max_nodes} nodes to conserve API calls")
                nodes = nodes[:max_nodes]
                
            return nodes

    def get_graph_context(self, node_id):
        """
        For a given HAZOP node, fetches information about the component it analyzes
        and its immediate neighbors in the graph to provide local context to the AI.
        """
        with self.driver.session() as session:
            # Cypher query to find the component and its neighbors within 2 hops.
            query = """
            MATCH (n:HAZOPNode {nodeID: $node_id})-[:ANALYZES]->(comp)
            OPTIONAL MATCH (comp)-[*1..2]-(neighbor)
            WITH comp, collect(DISTINCT neighbor.name) AS neighborNames
            RETURN 'Component ' + comp.name + ' (' + labels(comp)[0] + ')' AS componentInfo, 
                   neighborNames
            """
            result = session.run(query, node_id=node_id).single()
            if result:
                component_info = result['componentInfo']
                # Limit to 3 neighbors to keep the prompt concise.
                neighbor_names = result['neighborNames'][:3]
                return f"{component_info} connected to: {', '.join(filter(None, neighbor_names))}"
            return "No context found."
            
    def get_chemical_context(self, node_id):
        """
        New method to retrieve chemical/MSDS data for the HAZOP node
        """
        with self.driver.session() as session:
            query = """
            MATCH (n:HAZOPNode {nodeID: $node_id})-[:ANALYZES]->(comp)
            OPTIONAL MATCH (comp)-[:CONTAINS]->(chem:Chemical)
            WITH chem
            WHERE chem IS NOT NULL
            RETURN chem.name AS chemical_name,
                   chem.signalWord AS signal_word,
                   chem.physicalAndChemicalProperties_flashPoint AS flash_point,
                   chem.physicalAndChemicalProperties_autoignitionTemperature AS autoignition_temp,
                   chem.toxicologicalInformation_healthEffects AS health_effects,
                   chem.stabilityAndReactivity_reactivityHazards AS reactivity_hazards,
                   chem.stabilityAndReactivity_incompatibleMaterials AS incompatible_materials
            """
            results = session.run(query, node_id=node_id).data()

            if not results:
                return "No chemical data available for this node."

            chemical_info = []
            for result in results:
                info = f"Chemical: {result['chemical_name']} - "
                info += f"Signal: {result['signal_word']}, "
                info += f"Flash Point: {result['flash_point']}, "
                info += f"Health Effects: {result['health_effects']}, "
                info += f"Reactivity: {result['reactivity_hazards']}"
                chemical_info.append(info)

            return "; ".join(chemical_info)

    def get_operating_conditions(self, node_id):
        """
        New method to retrieve operating conditions for the HAZOP node
        """
        with self.driver.session() as session:
            query = """
            MATCH (n:HAZOPNode {nodeID: $node_id})-[:ANALYZES]->(comp)
            RETURN comp.name AS component_name,
                   comp.operatingParameters_temperature AS operating_temp,
                   comp.operatingParameters_pressure AS operating_pressure,
                   comp.designLimits_designTemperature AS design_temp,
                   comp.designLimits_designPressure AS design_pressure,
                   comp.materialOfConstruction AS material
            """
            results = session.run(query, node_id=node_id).data()
            if not results:
                return "No operating conditions available."
            conditions = []
            for result in results:
                condition = f"{result['component_name']}: "
                condition += f"Op Temp: {result['operating_temp']}, "
                condition += f"Op Press: {result['operating_pressure']}, "
                condition += f"Material: {result['material']}"
                conditions.append(condition)
            return "; ".join(conditions)


    def perform_batch_analysis(self, deviations):
        """
        Performs the core analysis for a batch of deviations.
        It builds the prompt, checks the cache, calls the Gemini API, and parses the result.
        """
        if not deviations:
            return None

        if self.api_call_count >= self.max_api_calls:
            print(f"API call limit reached ({self.max_api_calls}). Stopping analysis.")
            return None

        node_id = deviations[0]['nodeID']
        
        deviation_str = str(sorted([d['deviationID'] for d in deviations]))
        cache_key = self._get_cache_key(f"{node_id}_{deviation_str}")
        
        cached_result = self._load_from_cache(cache_key)
        if cached_result is not None:
            print(f"Using cached analysis for node {node_id}")
            return cached_result

        graph_context = self.get_graph_context(node_id)
        chemical_context = self.get_chemical_context(node_id)
        operating_conditions = self.get_operating_conditions(node_id)

        deviation_list_str = "\n".join([f"- {d['deviationID']}: {d['description']}" for d in deviations])
        
        combined_rag_query = " ".join([d['description'] for d in deviations])[:500]
        rag_context = self.rag_builder.search(combined_rag_query, k=2)

        prompt = f"""You are a Senior Process Safety Engineer with over 30 years of experience...
        [... The rest of your detailed prompt remains the same ...]
        CRITICAL: Provide only the JSON object with no additional text or explanations."""
        
        try:
            print(f"Making HAZOP API call {self.api_call_count + 1}/{self.max_api_calls} for node {node_id}")
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
            
            res = json.loads(response_text)
            self.api_call_count += 1
            
            calculator = LLMConfidenceCalculator()
            for dev_id in res:
                for cat in res[dev_id]:
                    for item in res[dev_id].get(cat, []):
                        confidence = calculator.calculate_combined_confidence(
                            text=item['description'],
                            rag_context=rag_context
                        )
                        item['confidenceLevel'] = confidence
            
            self._save_to_cache(cache_key, res)
            
            return res
            
        except json.JSONDecodeError as e:
            print(f"JSON decoding error for node {node_id}: {e}")
            print(f"Raw response: {response.text}")
            self.api_call_count += 1
            return None
        except Exception as e:
            print(f"Analysis error for node {node_id}: {e}")
            self.api_call_count += 1
            return None

    # +++ NEW METHOD TO UPDATE THE GRAPH +++
    def update_graph_with_results(self, analysis_results):
        """
        Writes the generated HAZOP analysis results back into the Neo4j graph.

        This function creates Deviation, Cause, Consequence, and Safeguard nodes
        and links them to the appropriate HAZOPNode.
        """
        print("\nUpdating knowledge graph with HAZOP analysis results...")
        with self.driver.session() as session:
            for result in tqdm(analysis_results, desc="Writing to Neo4j"):
                # Use a transaction for each result to ensure atomicity
                tx = session.begin_transaction()
                try:
                    # 1. Find the parent HAZOP Node and create the Deviation node
                    # The 'node' key in the result holds the HAZOP node's description
                    hazop_node_desc = result['node']
                    deviation_desc = result['deviation']
                    
                    tx.run("""
                    MATCH (hn:HAZOPNode {description: $hazop_node_desc})
                    MERGE (d:Deviation {description: $deviation_desc})
                    MERGE (hn)-[:HAS_DEVIATION]->(d)
                    """, hazop_node_desc=hazop_node_desc, deviation_desc=deviation_desc)

                    # 2. Process and link Causes
                    for cause in result.get('causes', []):
                        tx.run("""
                        MATCH (d:Deviation {description: $deviation_desc})
                        MERGE (c:Cause {description: $cause_desc})
                        SET c += $props
                        MERGE (d)-[:HAS_CAUSE]->(c)
                        """, deviation_desc=deviation_desc, cause_desc=cause['description'], props=cause)

                    # 3. Process and link Consequences
                    for consequence in result.get('consequences', []):
                        tx.run("""
                        MATCH (d:Deviation {description: $deviation_desc})
                        MERGE (co:Consequence {description: $consequence_desc})
                        SET co += $props
                        MERGE (d)-[:HAS_CONSEQUENCE]->(co)
                        """, deviation_desc=deviation_desc, consequence_desc=consequence['description'], props=consequence)
                    
                    # 4. Process and link Safeguards
                    for safeguard in result.get('safeguards', []):
                        tx.run("""
                        MATCH (d:Deviation {description: $deviation_desc})
                        MERGE (s:Safeguard {description: $safeguard_desc})
                        SET s += $props
                        MERGE (d)-[:HAS_SAFEGUARD]->(s)
                        """, deviation_desc=deviation_desc, safeguard_desc=safeguard['description'], props=safeguard)

                    tx.commit()
                except Exception as e:
                    print(f"Error during transaction for deviation '{deviation_desc}': {e}")
                    tx.rollback()
        print("Knowledge graph update complete.")


def main():
    """
    The main execution function that runs the entire analysis pipeline.
    """
    engine = AnalysisEngine(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
    
    max_nodes = getattr(config, 'MAX_NODES_TO_ANALYZE', 5)
    max_deviations_per_node = getattr(config, 'MAX_DEVIATIONS_PER_NODE', 10)
    
    hazop_nodes = engine.get_hazop_nodes(max_nodes)
    if not hazop_nodes:
        print("No HAZOP nodes found. Run script 03 first.")
        engine.close()
        return
    
    print(f"Processing {len(hazop_nodes)} nodes with up to {max_deviations_per_node} deviations each")
    all_results_for_report = []
        
    for node in tqdm(hazop_nodes, desc="Analyzing HAZOP Nodes"):
        if engine.api_call_count >= engine.max_api_calls:
            print("API limit reached, stopping node processing")
            break
            
        deviations_for_node = engine.deviation_generator.generate_deviations_for_node(
            node['nodeID'], 
            max_deviations=max_deviations_per_node
        )
        
        chunk_size = getattr(config, 'HAZOP_CHUNK_SIZE', 4)
        all_batch_results = {}

        for i in tqdm(range(0, len(deviations_for_node), chunk_size), 
                     desc=f"Analyzing {node['nodeID']}", leave=False):
            
            if engine.api_call_count >= engine.max_api_calls:
                print("API limit reached during chunk processing")
                break
                
            chunk = deviations_for_node[i:i + chunk_size]
            chunk_analysis_results = engine.perform_batch_analysis(chunk)
            
            if chunk_analysis_results:
                all_batch_results.update(chunk_analysis_results)
            
            time.sleep(3)

        if all_batch_results:
            for deviation in deviations_for_node:
                dev_id = deviation['deviationID']
                if dev_id in all_batch_results:
                    analysis_result = all_batch_results[dev_id]
                    # The 'node' key here must match the HAZOPNode's description property
                    report_row = {
                        'node': node['description'],
                        'guideword': deviation['guideword'],
                        'parameter': deviation['parameter'],
                        'deviation': deviation['description'],
                        'causes': analysis_result.get('causes', []),
                        'consequences': analysis_result.get('consequences', []),
                        'safeguards': analysis_result.get('safeguards', [])
                    }
                    all_results_for_report.append(report_row)
        
        engine.processed_nodes += 1
    
    # --- Save Final Results ---
    with open(config.HAZOP_RESULTS_JSON_PATH, 'w') as f:
        json.dump(all_results_for_report, f, indent=4)
    print(f"Saved analysis results to {config.HAZOP_RESULTS_JSON_PATH}")

    # +++ CALL THE NEW GRAPH UPDATE METHOD +++
    if all_results_for_report:
        engine.update_graph_with_results(all_results_for_report)
    else:
        print("No results to update in the graph.")

    engine.close()
    print("Phase 4: HAZOP Analysis Engine complete.")

if __name__ == "__main__":
    main()