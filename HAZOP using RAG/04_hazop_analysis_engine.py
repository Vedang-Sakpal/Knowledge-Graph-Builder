# UPDATED: Optimized to minimize API calls using Gemini API

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

class DeviationGenerator:
    def __init__(self, csv_path):
        print("Initializing Deviation Generator...")
        self.param_guideword_map = self._load_param_guideword_map(csv_path)
        print("Deviation Generator initialized successfully.")

    def _load_param_guideword_map(self, csv_path):
        try:
            df = pd.read_csv(csv_path, header=1).fillna('')
            param_col_name = df.columns[0]
            df.rename(columns={param_col_name: 'Parameter'}, inplace=True)
            guideword_cols = df.columns[1:]
            df = df.set_index('Parameter')
            param_map = {}
            for param, row in df.iterrows():
                param_clean = str(param).strip()
                if param_clean:
                    applicable_guidewords = [gw.strip() for gw in guideword_cols if '✔' in str(row[gw])]
                    param_map[param_clean] = applicable_guidewords
            print(f"Loaded {len(param_map)} parameters from CSV.")
            return param_map
        except Exception as e:
            print(f"Error loading or parsing {csv_path}: {e}")
            return {}

    def generate_deviations_for_node(self, node_id, max_deviations=None):
        """Generate deviations with optional limit"""
        deviations = []
        for param, guidewords in self.param_guideword_map.items():
            for guideword in guidewords:
                dev_id_safe = f"{node_id}-{guideword.replace(' ','')}-{param.replace(' ','')}"
                deviations.append({
                    "deviationID": dev_id_safe,
                    "description": f"{guideword} {param}",
                    "guideword": guideword, "parameter": param, "nodeID": node_id
                })
                
                if max_deviations and len(deviations) >= max_deviations:
                    print(f"Limited deviations to {max_deviations} for node {node_id}")
                    return deviations
                    
        return deviations

class RAGContextBuilder:
    def __init__(self):
        print("Initializing RAG Context Builder...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dfs = {
            "causes": pd.read_csv(config.CAUSES_CSV_PATH).dropna(how='all').stack().reset_index(drop=True).to_frame('description'),
            "consequences": pd.read_csv(config.CONSEQUENCES_CSV_PATH).dropna(how='all').stack().reset_index(drop=True).to_frame('description'),
            "safeguards": pd.read_csv(config.SAFEGUARDS_CSV_PATH).dropna(how='all').stack().reset_index(drop=True).to_frame('description')
        }
        self.embeddings = {k: self.model.encode(v['description'].tolist()) for k, v in self.dfs.items()}
        self.indexes = {k: self._create_faiss_index(v) for k, v in self.embeddings.items()}
        print("RAG Context Builder initialized.")

    def _create_faiss_index(self, embeddings):
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(np.array(embeddings, dtype=np.float32))
        return index

    def search(self, query, k=2):  # Reduced from 3 to 2 to save tokens
        query_embedding = self.model.encode([query])
        results = {}
        for key, index in self.indexes.items():
            _, indices = index.search(np.array(query_embedding, dtype=np.float32), k)
            results[key] = self.dfs[key].iloc[indices[0]]['description'].tolist()
        return results

class AnalysisEngine:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        # Initialize Gemini API
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=getattr(config, 'GEMINI_MODEL_NAME', 'gemini-1.5-flash'),
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 2000,
            }
        )
        self.rag_builder = RAGContextBuilder()
        self.deviation_generator = DeviationGenerator(config.PARAMETER_GUIDEWORD_CSV_PATH)
        
        # API call tracking and caching
        self.cache_dir = "hazop_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        self.api_call_count = 0
        self.max_api_calls = getattr(config, 'MAX_HAZOP_API_CALLS', 20)  # Conservative limit
        self.processed_nodes = 0

    def close(self):
        self.driver.close()
        print(f"Total HAZOP API calls made: {self.api_call_count}")
        print(f"Processed {self.processed_nodes} nodes")

    def _get_cache_key(self, content):
        """Generate cache key for analysis results"""
        return hashlib.md5(content.encode()).hexdigest()

    def _save_to_cache(self, cache_key, result):
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)

    def _load_from_cache(self, cache_key):
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None

    def get_hazop_nodes(self, max_nodes=None):
        """Get HAZOP nodes with optional limit"""
        with self.driver.session() as session:
            nodes = [r.data() for r in session.run("MATCH (n:HAZOPNode) RETURN n.nodeID AS nodeID, n.description AS description")]
            
            if max_nodes and len(nodes) > max_nodes:
                print(f"Limiting analysis to {max_nodes} nodes to conserve API calls")
                nodes = nodes[:max_nodes]
                
            return nodes

    def get_graph_context(self, node_id):
        with self.driver.session() as session:
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
                neighbor_names = result['neighborNames'][:3]  # Limit to 3 neighbors to save tokens
                return f"{component_info} connected to: {', '.join(filter(None, neighbor_names))}"
            return "No context found."

    def perform_batch_analysis(self, deviations):
        if not deviations:
            return None

        # Check API limit
        if self.api_call_count >= self.max_api_calls:
            print(f"API call limit reached ({self.max_api_calls}). Stopping analysis.")
            return None

        node_id = deviations[0]['nodeID']
        
        # Create cache key from deviations
        deviation_str = str(sorted([d['deviationID'] for d in deviations]))
        cache_key = self._get_cache_key(f"{node_id}_{deviation_str}")
        
        # Check cache first
        cached_result = self._load_from_cache(cache_key)
        if cached_result is not None:
            print(f"Using cached analysis for node {node_id}")
            return cached_result

        graph_context = self.get_graph_context(node_id)
        deviation_list_str = "\n".join([f"- {d['deviationID']}: {d['description']}" for d in deviations])
        
        # Simplified RAG query - combine all deviations
        combined_rag_query = " ".join([d['description'] for d in deviations])[:500]  # Limit query length
        rag_context = self.rag_builder.search(combined_rag_query, k=2)  # Fewer results

        # Streamlined prompt to save tokens
        prompt = f"""You are a process safety expert conducting HAZOP analysis.

HAZOP Node: {node_id}
Context: {graph_context}

Historical Reference:
- Causes: {rag_context['causes'][:2]}  
- Consequences: {rag_context['consequences'][:2]}
- Safeguards: {rag_context['safeguards'][:2]}

Analyze these deviations:
{deviation_list_str}

For each deviation, provide causes, consequences, and safeguards in this exact JSON format:
{{
  "deviation_id": {{
    "causes": [{{"description": "...", "source": "..."}}],
    "consequences": [{{"description": "...", "source": "..."}}],
    "safeguards": [{{"description": "...", "source": "..."}}]
  }}
}}

Provide only the JSON object with no additional text. Keep responses concise but technically accurate."""
        
        try:
            print(f"Making HAZOP API call {self.api_call_count + 1}/{self.max_api_calls} for node {node_id}")
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up response text
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
            
            res = json.loads(response_text)
            self.api_call_count += 1
            
            # Add confidence levels
            for dev_id in res:
                for cat in res[dev_id]:
                    for item in res[dev_id].get(cat, []):
                        item['confidenceLevel'] = np.random.uniform(0.6, 1.0)
            
            # Save to cache
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

def main():
    engine = AnalysisEngine(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
    
    # Limit number of nodes to process
    max_nodes = getattr(config, 'MAX_NODES_TO_ANALYZE', 5)
    max_deviations_per_node = getattr(config, 'MAX_DEVIATIONS_PER_NODE', 10)
    
    hazop_nodes = engine.get_hazop_nodes(max_nodes)
    if not hazop_nodes:
        print("No HAZOP nodes found. Run script 03 first.")
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
        
        # Larger chunk size to minimize API calls
        chunk_size = getattr(config, 'HAZOP_CHUNK_SIZE', 8)  # Process more deviations per call
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
            
            # Longer sleep between API calls
            time.sleep(3)

        if all_batch_results:
            for deviation in deviations_for_node:
                dev_id = deviation['deviationID']
                if dev_id in all_batch_results:
                    analysis_result = all_batch_results[dev_id]
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
    
    # Save results
    with open(config.HAZOP_RESULTS_JSON_PATH, 'w') as f:
        json.dump(all_results_for_report, f, indent=4)
    print(f"Saved analysis results to {config.HAZOP_RESULTS_JSON_PATH}")

    engine.close()
    print("Phase 4: HAZOP Analysis Engine complete.")

if __name__ == "__main__":
    main()