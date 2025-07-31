# UPDATED: This script now uses the OpenAI API and a "chunking" strategy.

import config
from neo4j import GraphDatabase
import openai
import json
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from tqdm import tqdm
import time
import re

class DeviationGenerator:
    def __init__(self, csv_path):
        print("Initializing Deviation Generator...")
        self.param_guideword_map = self._load_param_guideword_map(csv_path)
        print("Deviation Generator initialized successfully.")

    def _load_param_guideword_map(self, csv_path):
        """
        Loads and parses the CSV to map parameters to applicable guidewords.
        This version is robustly designed for the user's specific two-line header format.
        """
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

    def generate_deviations_for_node(self, node_id):
        deviations = []
        for param, guidewords in self.param_guideword_map.items():
            for guideword in guidewords:
                dev_id_safe = f"{node_id}-{guideword.replace(' ','')}-{param.replace(' ','')}"
                deviations.append({
                    "deviationID": dev_id_safe,
                    "description": f"{guideword} {param}",
                    "guideword": guideword, "parameter": param, "nodeID": node_id
                })
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

    def search(self, query, k=3):
        query_embedding = self.model.encode([query])
        results = {}
        for key, index in self.indexes.items():
            _, indices = index.search(np.array(query_embedding, dtype=np.float32), k)
            results[key] = self.dfs[key].iloc[indices[0]]['description'].tolist()
        return results

class AnalysisEngine:
    def __init__(self, uri, user, password, api_key):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        openai.api_key = api_key
        self.rag_builder = RAGContextBuilder()
        self.deviation_generator = DeviationGenerator(config.PARAMETER_GUIDEWORD_CSV_PATH)

    def close(self):
        self.driver.close()

    def get_hazop_nodes(self):
        with self.driver.session() as session:
            return [r.data() for r in session.run("MATCH (n:HAZOPNode) RETURN n.nodeID AS nodeID, n.description AS description")]

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
                neighbor_names = result['neighborNames']
                return f"{component_info} is connected to: {', '.join(filter(None, neighbor_names))}"
            return "No specific context found."

    def perform_batch_analysis(self, deviations):
        if not deviations:
            return None

        node_id = deviations[0]['nodeID']
        graph_context = self.get_graph_context(node_id)
        deviation_list_str = "\n".join([f"- {d['deviationID']}: {d['description']}" for d in deviations])
        combined_rag_query = " ".join([d['description'] for d in deviations])
        rag_context = self.rag_builder.search(combined_rag_query)

        prompt = f"""
        You are a world-class Process Safety Engineer conducting a HAZOP study.
        Your task is to analyze a list of process deviations for a single HAZOP Node.

        **HAZOP Node:** {node_id}
        **Context from P&ID and Process KG:** {graph_context}
        
        **Context from Historical HAZOP Data (Reference Files):**
        - Similar Causes Found: {rag_context['causes']}
        - Similar Consequences Found: {rag_context['consequences']}
        - Similar Safeguards Found: {rag_context['safeguards']}

        **Deviations to Analyze:**
        {deviation_list_str}

        **Your Task:**
        For EACH deviation in the list above, identify its credible Causes, potential Consequences, and existing Safeguards.
        For every item you identify, provide a `source` tag ('P&ID', 'Causes.csv', 'LLM-Inferred', etc.).
        
        **Format your output as a single, large, valid JSON object.**
        The top-level keys of this JSON object MUST be the `deviationID`s from the list above.
        Each `deviationID` key should have a value which is another JSON object containing three keys: "causes", "consequences", and "safeguards".
        
        Example JSON format:
        {{
          "Node-Heat-Exchanger-More-Flow": {{
            "causes": [{{"description": "Control valve fails open", "source": "Causes.csv"}}],
            "consequences": [{{"description": "Overpressure of downstream vessel", "source": "LLM-Inferred"}}],
            "safeguards": [{{"description": "High pressure alarm", "source": "P&ID"}}]
          }},
          "Node-Heat-Exchanger-Less-Flow": {{
            "causes": [...],
            "consequences": [...],
            "safeguards": [...]
          }}
        }}
        """
        try:
            response = openai.chat.completions.create(
                model=config.LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a process safety expert. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            res = json.loads(response.choices[0].message.content)
            
            for dev_id in res:
                for cat in res[dev_id]:
                    for item in res[dev_id].get(cat, []):
                        item['confidenceLevel'] = np.random.uniform(0.6, 1.0)
            return res
        except json.JSONDecodeError as e:
            print(f"LLM batch analysis JSON decoding error for node {node_id}: {e}")
            print("--- Received Malformed Text from API ---")
            print(response.choices[0].message.content)
            print("----------------------------------------")
            return None
        except Exception as e:
            print(f"LLM batch analysis error for node {node_id}: {e}")
            return None

def main():
    engine = AnalysisEngine(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD, config.LLM_API_KEY)
    hazop_nodes = engine.get_hazop_nodes()
    if not hazop_nodes:
        print("No HAZOP nodes found. Run script 03 first.")
        return
    
    all_results_for_report = []
        
    for node in tqdm(hazop_nodes, desc="Analyzing HAZOP Nodes"):
        deviations_for_node = engine.deviation_generator.generate_deviations_for_node(node['nodeID'])
        
        chunk_size = 5
        all_batch_results = {}

        for i in tqdm(range(0, len(deviations_for_node), chunk_size), desc=f"Analyzing Chunks for {node['nodeID']}", leave=False):
            chunk = deviations_for_node[i:i + chunk_size]
            chunk_analysis_results = engine.perform_batch_analysis(chunk)
            
            if chunk_analysis_results:
                all_batch_results.update(chunk_analysis_results)
            
            print(f"Finished processing chunk. Waiting for 2 seconds to respect rate limits...")
            time.sleep(2)

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
    
    with open(config.HAZOP_RESULTS_JSON_PATH, 'w') as f:
        json.dump(all_results_for_report, f, indent=4)
    print(f"Successfully saved all analysis results to {config.HAZOP_RESULTS_JSON_PATH}")

    engine.close()
    print("Phase 4: HAZOP Analysis Engine complete.")

if __name__ == "__main__":
    main()
