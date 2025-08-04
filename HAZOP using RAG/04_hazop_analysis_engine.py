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
        
        Algorithm:
        1. Count uncertainty vs confidence keywords
        2. Analyze sentence structure and hedging language
        3. Look for qualifiers that indicate uncertainty
        4. Calculate ratio-based confidence score
        """
        if not text or not isinstance(text, str):
            return 0.5  # Default neutral confidence
            
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        # Count indicators
        uncertainty_count = sum(1 for word in words if word in self.uncertainty_keywords)
        confidence_count = sum(1 for word in words if word in self.confidence_keywords)
        
        # Look for hedging phrases
        hedging_patterns = [
            r'it is possible that',
            r'there may be',
            r'could potentially',
            r'might result in',
            r'appears to be',
            r'seems to',
            r'suggests that'
        ]
        
        hedging_count = sum(1 for pattern in hedging_patterns if re.search(pattern, text_lower))
        
        # Calculate base confidence
        total_words = len(words)
        if total_words == 0:
            return 0.5
            
        # Confidence formula
        uncertainty_penalty = (uncertainty_count + hedging_count) / total_words
        confidence_boost = confidence_count / total_words
        
        # Base confidence starts at 0.7, adjusted by language analysis
        base_confidence = 0.7
        confidence = base_confidence + confidence_boost - (uncertainty_penalty * 2)
        
        # Clamp between 0.3 and 0.95
        return max(0.3, min(0.95, confidence))

    def calculate_rag_similarity_confidence(self, generated_text, rag_context):
        """
        Method 2: Compare generated content with RAG context to estimate confidence
        
        Algorithm:
        1. Extract key terms from both generated text and RAG context
        2. Calculate semantic overlap
        3. Higher overlap = higher confidence (more grounded in historical data)
        4. Lower overlap = lower confidence (more speculative)
        """
        if not generated_text or not rag_context:
            return 0.5
            
        # Simple word-based similarity (in practice, you'd use embeddings)
        gen_words = set(re.findall(r'\b\w+\b', generated_text.lower()))
        
        # Combine all RAG context
        rag_text = ""
        for category in ['causes', 'consequences', 'safeguards']:
            if category in rag_context:
                rag_text += " ".join(rag_context[category])
        
        rag_words = set(re.findall(r'\b\w+\b', rag_text.lower()))
        
        if not gen_words or not rag_words:
            return 0.4  # Low confidence if no overlap possible
            
        # Calculate Jaccard similarity
        intersection = len(gen_words.intersection(rag_words))
        union = len(gen_words.union(rag_words))
        
        if union == 0:
            return 0.4
            
        similarity = intersection / union
        
        # Convert similarity to confidence (0.4 to 0.9 range)
        confidence = 0.4 + (similarity * 0.5)
        return min(0.9, confidence)

    def calculate_response_consistency_confidence(self, responses_list):
        """
        Method 3: Multiple sampling consistency check
        
        Algorithm:
        1. Generate same response multiple times with different temperature
        2. Compare consistency across responses
        3. High consistency = high confidence
        4. Low consistency = low confidence
        
        Note: This requires multiple API calls, so it's expensive
        """
        if len(responses_list) < 2:
            return 0.6  # Default if only one response
            
        # Simple consistency check - count similar key phrases
        all_phrases = []
        for response in responses_list:
            # Extract key phrases (simplified)
            phrases = re.findall(r'\b\w+(?:\s+\w+){1,3}\b', response.lower())
            all_phrases.extend(phrases)
        
        # Count phrase frequencies
        phrase_counts = Counter(all_phrases)
        
        # Calculate consistency
        total_phrases = len(all_phrases)
        repeated_phrases = sum(1 for count in phrase_counts.values() if count > 1)
        
        if total_phrases == 0:
            return 0.5
            
        consistency_ratio = repeated_phrases / total_phrases
        
        # Convert to confidence
        confidence = 0.5 + (consistency_ratio * 0.4)
        return min(0.9, confidence)

    def calculate_length_complexity_confidence(self, text):
        """
        Method 4: Analyze response detail and complexity
        
        Algorithm:
        1. Longer, more detailed responses often indicate higher confidence
        2. Technical terminology suggests domain knowledge
        3. Specific numbers/measurements indicate precision
        4. Generic responses suggest lower confidence
        """
        if not text:
            return 0.3
            
        # Length factor
        word_count = len(re.findall(r'\b\w+\b', text))
        length_confidence = min(0.3, word_count / 100)  # Cap at 0.3 contribution
        
        # Technical terminology (simplified check)
        technical_terms = [
            'pressure', 'temperature', 'flow', 'valve', 'pump', 'reactor',
            'distillation', 'separation', 'catalyst', 'corrosion', 'erosion',
            'combustion', 'explosion', 'toxic', 'flammable', 'hazardous'
        ]
        
        tech_term_count = sum(1 for term in technical_terms if term in text.lower())
        tech_confidence = min(0.2, tech_term_count / 10)  # Cap at 0.2 contribution
        
        # Specific measurements/numbers
        number_pattern = r'\b\d+(?:\.\d+)?\s*(?:bar|psi|°C|°F|kg|l|m³|%)\b'
        specific_numbers = len(re.findall(number_pattern, text))
        number_confidence = min(0.2, specific_numbers / 5)  # Cap at 0.2 contribution
        
        # Base confidence
        base_confidence = 0.5
        
        total_confidence = base_confidence + length_confidence + tech_confidence + number_confidence
        return min(0.95, total_confidence)

    def calculate_combined_confidence(self, text, rag_context=None, responses_list=None):
        """
        Method 5: Combined approach using multiple indicators
        
        Algorithm:
        1. Calculate confidence using multiple methods
        2. Weight each method based on reliability
        3. Combine into final confidence score
        """
        confidences = []
        weights = []
        
        # Linguistic analysis (weight: 0.3)
        ling_conf = self.calculate_linguistic_confidence(text)
        confidences.append(ling_conf)
        weights.append(0.3)
        
        # Length/complexity analysis (weight: 0.2)
        complex_conf = self.calculate_length_complexity_confidence(text)
        confidences.append(complex_conf)
        weights.append(0.2)
        
        # RAG similarity (weight: 0.4) - if available
        if rag_context:
            rag_conf = self.calculate_rag_similarity_confidence(text, rag_context)
            confidences.append(rag_conf)
            weights.append(0.4)
        else:
            # Redistribute weight if RAG not available
            weights[0] += 0.2  # More weight to linguistic
            weights[1] += 0.2  # More weight to complexity
        
        # Response consistency (weight: 0.1) - if available
        if responses_list and len(responses_list) > 1:
            consist_conf = self.calculate_response_consistency_confidence(responses_list)
            confidences.append(consist_conf)
            weights.append(0.1)
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w/total_weight for w in weights]
        
        # Calculate weighted average
        final_confidence = sum(c*w for c, w in zip(confidences, weights))
        
        return final_confidence

# Example usage in HAZOP context
def integrate_real_confidence_into_hazop(analysis_result, rag_context=None):
    """
    How to integrate real confidence calculation into your HAZOP analysis
    """
    calculator = LLMConfidenceCalculator()
    
    # Process each category
    for category in ['causes', 'consequences', 'safeguards']:
        if category in analysis_result:
            for item in analysis_result[category]:
                if isinstance(item, dict) and 'description' in item:
                    # Calculate real confidence instead of random number
                    confidence = calculator.calculate_combined_confidence(
                        text=item['description'],
                        rag_context=rag_context
                    )
                    item['confidenceLevel'] = confidence
                    
                    # Add explanation of confidence factors
                    item['confidenceFactors'] = {
                        'linguistic': calculator.calculate_linguistic_confidence(item['description']),
                        'complexity': calculator.calculate_length_complexity_confidence(item['description']),
                        'rag_similarity': calculator.calculate_rag_similarity_confidence(
                            item['description'], rag_context) if rag_context else None
                    }
    
    return analysis_result

# Advanced: Using model probabilities (if API supports it)
def calculate_token_probability_confidence(model_response):
    """
    Method 6: Use actual token probabilities from the model (if available)
    
    Algorithm:
    1. Get log probabilities for each generated token
    2. Calculate perplexity or average probability
    3. Higher average probability = higher confidence
    4. Lower perplexity = higher confidence
    
    Note: This requires API access to token probabilities
    """
    # Pseudo-code - actual implementation depends on API
    if hasattr(model_response, 'token_probabilities'):
        probs = model_response.token_probabilities
        if probs:
            # Calculate average log probability
            avg_log_prob = sum(probs) / len(probs)
            # Convert to confidence (higher log prob = higher confidence)
            confidence = min(0.95, max(0.1, (avg_log_prob + 10) / 10))
            return confidence
    
    return 0.5  # Default if probabilities not available

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

        # Stop if the API call safety limit has been reached.
        if self.api_call_count >= self.max_api_calls:
            print(f"API call limit reached ({self.max_api_calls}). Stopping analysis.")
            return None

        node_id = deviations[0]['nodeID']
        
        # --- Caching Logic ---
        # Create a unique key based on the node and the specific deviations being analyzed.
        deviation_str = str(sorted([d['deviationID'] for d in deviations]))
        cache_key = self._get_cache_key(f"{node_id}_{deviation_str}")
        
        cached_result = self._load_from_cache(cache_key)
        if cached_result is not None:
            print(f"Using cached analysis for node {node_id}")
            return cached_result

        # --- Prompt Engineering ---
        # 1. Get graph context from Neo4j.
        graph_context = self.get_graph_context(node_id)
        chemical_context = self.get_chemical_context(node_id)  # New method to get MSDS data
        operating_conditions = self.get_operating_conditions(node_id)  # New method for process conditions

        # 2. Format the list of deviations for the prompt.
        deviation_list_str = "\n".join([f"- {d['deviationID']}: {d['description']}" for d in deviations])
        
        # 3. Get RAG context by searching for similar historical examples.
        combined_rag_query = " ".join([d['description'] for d in deviations])[:500]
        rag_context = self.rag_builder.search(combined_rag_query, k=2)

        # 4. Assemble the final, streamlined prompt for the AI.
        prompt = f"""You are a Senior Process Safety Engineer with over 30 years of experience in chemical process industries, specializing in HAZOP studies, risk assessment, and process safety management. You have extensive expertise in:
- Chemical process hazards and failure modes
- Process safety management systems (PSM)
- Incident investigation and root cause analysis
- Safety instrumented systems (SIS) design
- Chemical reactivity and toxicology
- Fire and explosion prevention
- Regulatory compliance (OSHA PSM, EPA RMP, IEC 61511)

CURRENT HAZOP ANALYSIS CONTEXT:
=================================
HAZOP Node: {node_id}
Process Context: {graph_context}
Operating Conditions: {operating_conditions}
Chemical Inventory: {chemical_context}

HISTORICAL PRECEDENTS FROM YOUR EXPERIENCE:
==========================================
Similar Causes from Past Studies: {'; '.join(rag_context['causes'][:3])}
Historical Consequences: {'; '.join(rag_context['consequences'][:3])}
Proven Safeguards: {'; '.join(rag_context['safeguards'][:3])}

DEVIATIONS TO ANALYZE:
=====================
{deviation_list_str}

ANALYSIS REQUIREMENTS:
=====================
For each deviation, apply your 30+ years of professional experience to provide:

1. **CAUSES**: Identify realistic failure modes considering:
   - Equipment degradation mechanisms (corrosion, erosion, fatigue)
   - Human factors and operational errors
   - Process chemistry interactions
   - Environmental factors
   - Maintenance-related failures
   - Control system failures
   - External events (power loss, instrument air failure)

2. **CONSEQUENCES**: Assess potential outcomes considering:
   - Chemical hazard properties from MSDS data (toxicity, flammability, reactivity)
   - Process conditions (temperature, pressure, inventory)
   - Escalation potential and domino effects
   - Personnel exposure scenarios
   - Environmental release consequences
   - Business continuity impacts
   - Regulatory implications

3. **SAFEGUARDS**: Recommend defense layers following hierarchy of controls:
   - Inherent safety measures (substitute, minimize, moderate, simplify)
   - Passive engineered safeguards (containment, relief systems)
   - Active engineered safeguards (detection, control systems, SIS)
   - Procedural safeguards (procedures, training, inspection)
   - Emergency response measures

PROFESSIONAL STANDARDS:
======================
- Reference specific industry standards (API, ASME, IEC, ISA) where applicable
- Consider quantitative risk criteria and ALARP principles
- Apply lessons learned from major incidents (Bhopal, Texas City, etc.)
- Ensure recommendations are practical and cost-effective
- Consider maintenance requirements and human factors
- Address both acute and chronic exposure scenarios

RESPONSE FORMAT:
===============
Provide your analysis in this exact JSON format:

{{
  "deviation_id": {{
    "causes": [
      {{
        "description": "Detailed technical cause with specific failure mechanism",
        "source": "Equipment/Human/Process/External",
        "likelihood": "High/Medium/Low",
        "precedent": "Reference to similar industry incident if applicable"
      }}
    ],
    "consequences": [
      {{
        "description": "Specific consequence considering chemical hazards and process conditions",
        "source": "Fire/Explosion/Toxic Release/Environmental/Business",
        "severity": "High/Medium/Low", 
        "affected_systems": "Personnel/Environment/Equipment/Production",
        "msds_basis": "Relevant MSDS hazard information supporting this consequence"
      }}
    ],
    "safeguards": [
      {{
        "description": "Specific safeguard with implementation details",
        "source": "Inherent/Passive/Active/Procedural/Emergency",
        "sil_requirement": "SIL level if applicable (SIL 1/2/3/4 or N/A)",
        "standard_reference": "Applicable industry standard (API RP 14C, IEC 61511, etc.)",
        "effectiveness": "High/Medium/Low"
      }}
    ]
  }}
}}

Draw upon your decades of experience in process safety to provide thorough, technically sound, and practically implementable recommendations. Consider the specific chemical hazards present and ensure your analysis reflects current industry best practices and lessons learned from historical incidents.

CRITICAL: Provide only the JSON object with no additional text or explanations."""
        
        try:
            print(f"Making HAZOP API call {self.api_call_count + 1}/{self.max_api_calls} for node {node_id}")
            
            # --- API Call ---
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up the response to ensure it's valid JSON.
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
            
            # Parse the JSON string into a Python dictionary.
            res = json.loads(response_text)
            self.api_call_count += 1
            
            # (Optional) Add a random confidence level for demonstration purposes.
            for dev_id in res:
                for cat in res[dev_id]:
                    for item in res[dev_id].get(cat, []):
                        calculator = LLMConfidenceCalculator()
                        confidence = calculator.calculate_combined_confidence(
                            text=item['description'],
                            rag_context=rag_context
                        )
                        item['confidenceLevel'] = confidence
            
            # Save the successful result to the cache.
            self._save_to_cache(cache_key, res)
            
            return res
            
        except json.JSONDecodeError as e:
            print(f"JSON decoding error for node {node_id}: {e}")
            print(f"Raw response: {response.text}")
            self.api_call_count += 1 # Count a failed parse as an API call
            return None
        except Exception as e:
            print(f"Analysis error for node {node_id}: {e}")
            self.api_call_count += 1 # Count a general error as an API call
            return None
        


def main():
    """
    The main execution function that runs the entire analysis pipeline.
    """
    engine = AnalysisEngine(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
    
    # Get configurable limits for the run from the config file.
    max_nodes = getattr(config, 'MAX_NODES_TO_ANALYZE', 5)
    max_deviations_per_node = getattr(config, 'MAX_DEVIATIONS_PER_NODE', 10)
    
    hazop_nodes = engine.get_hazop_nodes(max_nodes)
    if not hazop_nodes:
        print("No HAZOP nodes found. Run script 03 first.")
        return
    
    print(f"Processing {len(hazop_nodes)} nodes with up to {max_deviations_per_node} deviations each")
    all_results_for_report = []
        
    # --- Main Loop: Iterate over each HAZOP node ---
    for node in tqdm(hazop_nodes, desc="Analyzing HAZOP Nodes"):
        if engine.api_call_count >= engine.max_api_calls:
            print("API limit reached, stopping node processing")
            break
            
        # 1. Generate all potential deviations for the current node.
        deviations_for_node = engine.deviation_generator.generate_deviations_for_node(
            node['nodeID'], 
            max_deviations=max_deviations_per_node
        )
        
        # 2. Process deviations in batches (chunks) to minimize API calls.
        chunk_size = getattr(config, 'HAZOP_CHUNK_SIZE', 4)
        all_batch_results = {}

        # Loop through the deviations in chunks.
        for i in tqdm(range(0, len(deviations_for_node), chunk_size), 
                     desc=f"Analyzing {node['nodeID']}", leave=False):
            
            if engine.api_call_count >= engine.max_api_calls:
                print("API limit reached during chunk processing")
                break
                
            chunk = deviations_for_node[i:i + chunk_size]
            # 3. Perform the analysis on the current chunk.
            chunk_analysis_results = engine.perform_batch_analysis(chunk)
            
            if chunk_analysis_results:
                all_batch_results.update(chunk_analysis_results)
            
            # Pause briefly between API calls to avoid overwhelming the service.
            time.sleep(3)

        # 4. Collate the results from all batches for the current node.
        if all_batch_results:
            for deviation in deviations_for_node:
                dev_id = deviation['deviationID']
                if dev_id in all_batch_results:
                    analysis_result = all_batch_results[dev_id]
                    # Format the result into a clean structure for the final report.
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
    # 5. Save the complete list of results to a single JSON file.
    with open(config.HAZOP_RESULTS_JSON_PATH, 'w') as f:
        json.dump(all_results_for_report, f, indent=4)
    print(f"Saved analysis results to {config.HAZOP_RESULTS_JSON_PATH}")

    # Clean up the database connection.
    engine.close()
    print("Phase 4: HAZOP Analysis Engine complete.")

# Standard Python entry point.
if __name__ == "__main__":
    main()