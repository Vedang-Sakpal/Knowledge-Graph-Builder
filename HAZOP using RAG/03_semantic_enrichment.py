import config
from neo4j import GraphDatabase
import google.genai as genai
from google.genai.types import GenerateContentConfig
import json
import os
import fitz
import time

class PIDChemicalProcessor:
    """
    A specialized processor for P&ID boundary analysis and chemical node creation.
    This class handles:
    1. Processing P&ID boundaries to extract chemical information
    2. Creating Chemical nodes with appropriate relationships
    3. Extracting detailed chemical properties from MSDS files
    4. Updating Neo4j database with structured chemical data
    """
    
    def __init__(self, uri, user, password):
        """Initialize the processor with Neo4j and Gemini API connections."""
        # Neo4j database connection
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # Gemini API setup
        self.genai_client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model_name = getattr(config, 'GEMINI_MODEL_NAME', 'gemini-2.5-flash')
        self.generation_config = GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=2000,
        )
        
        
        # Track processed data for final report
        self.processed_chemicals = []
        self.created_relationships = []
    
    def close(self):
        """Close database connection and print session summary."""
        self.driver.close()
        print("\nSession Summary:")
        #print(f"Total API calls made: {self.api_call_count}")
        print(f"Chemicals processed: {len(self.processed_chemicals)}")
        print(f"Relationships created: {len(self.created_relationships)}")
    
    # --- File Processing Methods ---
    def read_msds_file(self, file_path):
        """Extract text from MSDS files (PDF, TXT, MD)."""
        try:
            if file_path.lower().endswith('.pdf'):
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text("text")
                doc.close()
                return text
            elif file_path.lower().endswith(('.txt', '.md')):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                print(f"Unsupported file format: {file_path}")
                return None
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    def extract_with_llm(self, content, prompt, prompt_type):
        """Extract information using Gemini LLM with caching."""
#        if self.api_call_count >= self.max_api_calls:
#            print(f"API call limit ({self.max_api_calls}) reached.")
#            return None
        
        
#        print(f"Making API call {self.api_call_count + 1}/{self.max_api_calls} for {prompt_type}")
        
        # Truncate content if too long
        max_length = getattr(config, 'MAX_CONTEXT_LENGTH', 10000)
        if len(content) > max_length:
            content = content[:max_length] + "...[truncated]"
        
        full_prompt = f"""You are an expert data extraction specialist. Extract information in valid JSON format only.

{prompt}

---CONTENT---
{content}

Respond with valid JSON only, no additional text or explanations."""
        
        try:
            response = self.genai_client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=self.generation_config,
            )
            
            response_text = (response.text or "").strip()
            
            # Clean JSON response
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
            
            result = json.loads(response_text)
#            self.api_call_count += 1
            
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw response: {response.text}")
#            self.api_call_count += 1
            return None
        except Exception as e:
            print(f"API call error: {e}")
#            self.api_call_count += 1
            return None
    
    # --- P&ID Boundary Processing ---
    def find_boundary_nodes(self):
        """Find all boundary nodes in the Neo4j database with tag and type information."""
        print("\n=== Step 1: Finding P&ID Boundary Nodes ===")
        
        with self.driver.session() as session:
            # Updated query to match your data structure
            query = """
            MATCH (b:Boundary)
            RETURN b.name as tag, 
                   b.type as boundary_type, 
                   b.chemical as chemical,
                   b.data as data,
                   properties(b) as all_properties,
                   elementId(b) as node_id
            ORDER BY b.name
            """
            
            result = session.run(query)
            boundaries = []
            
            for record in result:
                boundary_data = {
                    'tag': record['tag'],
                    'boundary_type': record['boundary_type'],
                    'chemical': record['chemical'],
                    'data': record['data'],
                    'properties': record['all_properties'],
                    'node_id': record['node_id']
                }
                boundaries.append(boundary_data)
            
            print(f"Found {len(boundaries)} boundary nodes to process")
            
            # Print details of found boundaries for debugging
            for boundary in boundaries:
                print(f"  - {boundary['tag']}: type='{boundary['boundary_type']}', chemical='{boundary['chemical']}'")
            
            return boundaries
    
    def extract_chemical_from_boundary(self, boundary_data):
        """Extract chemical information from boundary node properties."""
        # For your data structure, the chemical name is directly available in the 'chemical' property
        chemical_name = boundary_data.get('chemical')
        
        if chemical_name:
            tag = boundary_data['tag']
            print(f"Found chemical '{chemical_name}' in boundary {tag}")
            return chemical_name.strip()
        
        # Fallback to original logic if no direct chemical property
        properties = boundary_data['properties']
        tag = boundary_data['tag']
        
        # Common fields that might contain chemical names
        chemical_fields = [
            'chemical', 'chemical_name', 'substance', 'material', 'fluid',
            'component', 'stream_name', 'stream', 'feed', 'product',
            'description', 'name', 'content', 'medium'
        ]
        
        # First, check direct chemical fields
        for field in chemical_fields:
            if field in properties and properties[field]:
                chemical_name = str(properties[field]).strip()
                if len(chemical_name) > 2:  # Valid chemical name
                    print(f"Found chemical '{chemical_name}' in field '{field}' for boundary {tag}")
                    return chemical_name
        
        # If no direct field, look in all string properties
        for key, value in properties.items():
            if isinstance(value, str) and value.strip():
                # Skip obviously non-chemical properties
                skip_fields = ['tag', 'type', 'id', 'node_id', 'x', 'y', 'width', 'height', 'label', 'name', 'data']
                if key.lower() not in skip_fields and len(value.strip()) > 2:
                    chemical_name = value.strip()
                    print(f"Extracted chemical '{chemical_name}' from property '{key}' for boundary {tag}")
                    return chemical_name
        
        print(f"No chemical information found for boundary {tag}")
        return None
    
    def create_chemical_nodes_and_relationships(self, boundaries):
        """Create Chemical nodes and relationships based on boundary types."""
        print("\n=== Step 2: Creating Chemical Nodes and Relationships ===")
        
        with self.driver.session() as session:
            for boundary in boundaries:
                tag = boundary['tag']
                boundary_type = str(boundary['boundary_type']).lower() if boundary['boundary_type'] else 'unknown'
                
                # Extract chemical name
                chemical_name = self.extract_chemical_from_boundary(boundary)
                
                if not chemical_name:
                    continue
                
                print(f"\nProcessing: {tag} (type: {boundary_type}) -> Chemical: {chemical_name}")
                
                # Create or merge Chemical node
                chemical_query = """
                MERGE (c:Chemical {name: $chemical_name})
                ON CREATE SET c.created_from_pid = true, c.created_timestamp = timestamp()
                RETURN c
                """
                session.run(chemical_query, chemical_name=chemical_name)
                
                # Create relationships based on boundary type
                relationship_created = False
                
                if boundary_type == 'source' or 'source' in boundary_type:
                    # Source boundary: Chemical -[INLET]-> Boundary
                    relationship_query = """
                    MATCH (c:Chemical {name: $chemical_name})
                    MATCH (b:Boundary) WHERE elementId(b) = $node_id
                    MERGE (c)-[r:INLET]->(b)
                    ON CREATE SET r.created_timestamp = timestamp()
                    RETURN type(r) as rel_type
                    """
                    session.run(relationship_query, chemical_name=chemical_name, node_id=boundary['node_id'])
                    relationship_type = "INLET"
                    relationship_direction = f"{chemical_name} -[INLET]-> {tag}"
                    relationship_created = True
                    print(f"Created relationship: {relationship_direction}")
                    
                elif boundary_type == 'sink' or 'sink' in boundary_type:
                    # Sink boundary: Boundary -[OUTLET]-> Chemical
                    relationship_query = """
                    MATCH (c:Chemical {name: $chemical_name})
                    MATCH (b:Boundary) WHERE elementId(b) = $node_id
                    MERGE (b)-[r:OUTLET]->(c)
                    ON CREATE SET r.created_timestamp = timestamp()
                    RETURN type(r) as rel_type
                    """
                    session.run(relationship_query, chemical_name=chemical_name, node_id=boundary['node_id'])
                    relationship_type = "OUTLET"
                    relationship_direction = f"{tag} -[OUTLET]-> {chemical_name}"
                    relationship_created = True
                    print(f"Created relationship: {relationship_direction}")
                    
                else:
                    # Default case - try to infer from context or create bidirectional
                    print(f"Unknown boundary type '{boundary_type}', creating default CONNECTED relationship")
                    relationship_query = """
                    MATCH (c:Chemical {name: $chemical_name})
                    MATCH (b:Boundary) WHERE elementId(b) = $node_id
                    MERGE (c)-[r:CONNECTED]-(b)
                    ON CREATE SET r.created_timestamp = timestamp()
                    RETURN type(r) as rel_type
                    """
                    session.run(relationship_query, chemical_name=chemical_name, node_id=boundary['node_id'])
                    relationship_type = "CONNECTED"
                    relationship_direction = f"{chemical_name} -[CONNECTED]- {tag}"
                    relationship_created = True
                    print(f"Created relationship: {relationship_direction}")
                
                # Track processed data
                chemical_data = {
                    'name': chemical_name,
                    'boundary_tag': tag,
                    'boundary_type': boundary_type,
                    'relationship_type': relationship_type,
                    'relationship_direction': relationship_direction,
                    'properties': {}
                }
                self.processed_chemicals.append(chemical_data)
                
                if relationship_created:
                    self.created_relationships.append({
                        'chemical': chemical_name,
                        'boundary': tag,
                        'type': relationship_type,
                        'direction': relationship_direction
                    })
    
    # --- MSDS Processing ---
    def process_msds_files(self, msds_directory):
        """Process MSDS files to extract detailed chemical properties."""
        print(f"\n=== Step 3: Processing MSDS Files from {msds_directory} ===")
        
        if not os.path.exists(msds_directory):
            print(f"MSDS directory not found: {msds_directory}")
            return
        
        msds_files = [f for f in os.listdir(msds_directory) 
                      if f.lower().endswith(('.pdf', '.txt', '.md'))]
        
        max_files = getattr(config, 'MAX_MSDS_FILES', 10)
        if len(msds_files) > max_files:
            msds_files = msds_files[:max_files]
            print(f"Processing first {max_files} MSDS files")
        
        print(f"Found {len(msds_files)} MSDS files to process")
        
        # Enhanced MSDS extraction prompt
        msds_prompt = """
        Extract detailed chemical properties from this Safety Data Sheet (SDS/MSDS).
        
        Required properties:
        1. `name`: Chemical/substance name (prefer generic over brand names)
        2. `type`: Material classification (e.g., 'Main input Feed', 'Intermediate', 'Product', 'Waste', 'Raw Material')
        3. `material_type`: Category (e.g., 'raw-material', 'intermediate', 'product', 'waste', 'catalyst')
        4. `physical_state`: State at room temperature ('solid', 'liquid', 'gas', 'mixture')
        5. `corrosive_nature`: Corrosiveness assessment ('corrosive', 'not-corrosive', 'mildly-corrosive')
        6. `flammable_nature`: Flammability assessment ('flammable', 'not-flammable', 'highly-flammable')
        7. `volatile_nature`: Volatility assessment ('volatile', 'non-volatile', 'semi-volatile')
        8. `toxic_nature`: Toxicity assessment ('toxic', 'non-toxic', 'mildly-toxic')
        9. `viscous_nature`: Viscosity assessment ('viscous', 'non-viscous', 'highly-viscous')
        
        Additional properties (if available):
        10. `cas_number`: CAS registry number
        11. `molecular_formula`: Chemical formula
        12. `molecular_weight`: Molecular weight with units
        13. `density`: Density value with units
        14. `boiling_point`: Boiling point with units
        15. `melting_point`: Melting point with units
        16. `flash_point`: Flash point with units
        17. `ph_value`: pH value or range
        18. `vapor_pressure`: Vapor pressure with units
        19. `solubility`: Solubility information
        20. `hazard_class`: Hazard classification
        
        Return as JSON object with all available properties.
        """
        
        for filename in msds_files:
#            if self.api_call_count >= self.max_api_calls:
#                print("API call limit reached, stopping MSDS processing")
#                break
            
            file_path = os.path.join(msds_directory, filename)
            print(f"\nProcessing MSDS: {filename}")
            
            # Read file content
            msds_content = self.read_msds_file(file_path)
            if not msds_content:
                continue
            
            # Extract properties using LLM
            extracted_data = self.extract_with_llm(msds_content, msds_prompt, f"MSDS_{filename}")
            
            if extracted_data and isinstance(extracted_data, dict):
                chemical_name = extracted_data.get('name')
                if chemical_name:
                    self.update_chemical_with_properties(chemical_name, extracted_data, filename)
                else:
                    print(f"No chemical name extracted from {filename}")
            else:
                print(f"Failed to extract data from {filename}")
            
            time.sleep(2)  # Rate limiting
    
    def update_chemical_with_properties(self, chemical_name, properties, msds_filename):
        """Update Chemical node with extracted properties from MSDS."""
        print(f"Updating chemical '{chemical_name}' with MSDS properties")
        
        with self.driver.session() as session:
            # Find the chemical and its connected boundaries
            boundary_query = """
            MATCH (c:Chemical {name: $chemical_name})
            OPTIONAL MATCH (c)-[:INLET]->(b:Boundary)
            OPTIONAL MATCH (b2:Boundary)-[:OUTLET]->(c)
            RETURN c, b.tag as inlet_boundary, b2.tag as outlet_boundary
            """
            
            result = session.run(boundary_query, chemical_name=chemical_name)
            record = result.single()
            
            if record:
                # Add source information from connected boundaries
                inlet_boundary = record.get('inlet_boundary')
                outlet_boundary = record.get('outlet_boundary')
                source_boundary = inlet_boundary or outlet_boundary
                
                if source_boundary:
                    properties['source'] = source_boundary
                
                # Flatten nested properties for Neo4j
                flattened_props = self._flatten_properties(properties)
                
                # Add metadata
                flattened_props['msds_source'] = msds_filename
                flattened_props['last_updated'] = int(time.time())
                
                # Update the chemical node
                update_query = """
                MATCH (c:Chemical {name: $chemical_name})
                SET c += $properties
                RETURN c
                """
                
                session.run(update_query, chemical_name=chemical_name, properties=flattened_props)
                
                print(f"Updated chemical '{chemical_name}' with {len(flattened_props)} properties")
                
                # Update tracking data
                for chem in self.processed_chemicals:
                    if chem['name'] == chemical_name:
                        chem['properties'].update(flattened_props)
                        chem['msds_source'] = msds_filename
                        break
            else:
                print(f"Chemical '{chemical_name}' not found in database, creating new node")
                # Create new chemical node
                flattened_props = self._flatten_properties(properties)
                flattened_props['msds_source'] = msds_filename
                flattened_props['created_from_msds'] = True
                flattened_props['created_timestamp'] = int(time.time())
                
                create_query = """
                CREATE (c:Chemical $properties)
                RETURN c
                """
                
                session.run(create_query, properties=flattened_props)
                
                # Add to tracking
                self.processed_chemicals.append({
                    'name': chemical_name,
                    'properties': flattened_props,
                    'msds_source': msds_filename,
                    'created_new': True
                })
    
    def _flatten_properties(self, props):
        """Flatten nested properties for Neo4j storage."""
        flattened = {}
        for key, value in props.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flattened[f"{key}_{sub_key}"] = sub_value
            elif isinstance(value, list):
                flattened[key] = str(value)
            else:
                flattened[key] = value
        return flattened
    
    # --- Final Report Generation ---
    def generate_final_report(self):
        """Generate comprehensive final report of all processed chemicals and relationships."""
        print("\n" + "="*100)
        print("FINAL REPORT: P&ID CHEMICAL PROCESSING RESULTS")
        print("="*100)
        
        if not self.processed_chemicals:
            print("No chemicals were processed in this session.")
            return
        
        print(f"\nTOTAL CHEMICALS PROCESSED: {len(self.processed_chemicals)}")
        print(f"TOTAL RELATIONSHIPS CREATED: {len(self.created_relationships)}")
        
        # Section 1: Chemical Nodes and Properties
        print("\n" + "-"*50)
        print("CHEMICAL NODES AND PROPERTIES")
        print("-"*50)
        
        for i, chemical in enumerate(self.processed_chemicals, 1):
            print(f"\n[{i}] CHEMICAL: {chemical['name']}")
            print(f"    └─ Boundary Connection: {chemical.get('boundary_tag', 'N/A')}")
            print(f"    └─ Boundary Type: {chemical.get('boundary_type', 'N/A')}")
            print(f"    └─ Relationship: {chemical.get('relationship_direction', 'N/A')}")
            
            if chemical.get('msds_source'):
                print(f"    └─ MSDS Source: {chemical['msds_source']}")
            
            if chemical['properties']:
                print(f"    └─ Properties ({len(chemical['properties'])} total):")
                
                # Group properties by category
                basic_props = {}
                physical_props = {}
                safety_props = {}
                other_props = {}
                
                for prop, value in chemical['properties'].items():
                    if prop in ['name', 'type', 'material_type', 'source']:
                        basic_props[prop] = value
                    elif prop in ['physical_state', 'density', 'boiling_point', 'melting_point', 'molecular_weight']:
                        physical_props[prop] = value
                    elif 'nature' in prop or prop in ['hazard_class', 'cas_number', 'flash_point']:
                        safety_props[prop] = value
                    else:
                        other_props[prop] = value
                
                if basic_props:
                    print("        ├─ Basic Properties:")
                    for prop, value in basic_props.items():
                        print(f"        │  • {prop}: {value}")
                
                if physical_props:
                    print("        ├─ Physical Properties:")
                    for prop, value in physical_props.items():
                        print(f"        │  • {prop}: {value}")
                
                if safety_props:
                    print("        ├─ Safety Properties:")
                    for prop, value in safety_props.items():
                        print(f"        │  • {prop}: {value}")
                
                if other_props:
                    print("        └─ Other Properties:")
                    for prop, value in other_props.items():
                        print(f"           • {prop}: {value}")
        
        # Section 2: Relationship Summary
        print("\n" + "-"*50)
        print("RELATIONSHIP SUMMARY")
        print("-"*50)
        
        relationship_types = {}
        for rel in self.created_relationships:
            rel_type = rel['type']
            if rel_type not in relationship_types:
                relationship_types[rel_type] = []
            relationship_types[rel_type].append(rel)
        
        for rel_type, relationships in relationship_types.items():
            print(f"\n{rel_type} Relationships ({len(relationships)}):")
            for rel in relationships:
                print(f"  • {rel['direction']}")
        
        # Section 3: Database Statistics
        print("\n" + "-"*50)
        print("DATABASE STATISTICS")
        print("-"*50)
        
        with self.driver.session() as session:
            # Count total chemicals
            result = session.run("MATCH (c:Chemical) RETURN count(c) as total")
            total_chemicals = result.single()['total']
            
            # Count chemicals with properties
            result = session.run("MATCH (c:Chemical) WHERE size(keys(c)) > 1 RETURN count(c) as enriched")
            enriched_chemicals = result.single()['enriched']
            
            # Count relationships
            result = session.run("MATCH ()-[r:INLET|OUTLET|CONNECTED]->() RETURN count(r) as total_rels")
            total_relationships = result.single()['total_rels']
            
            print(f"Total Chemical Nodes in Database: {total_chemicals}")
            print(f"Enriched Chemical Nodes: {enriched_chemicals}")
            print(f"Total Chemical-Boundary Relationships: {total_relationships}")
            print(f"Chemicals Processed This Session: {len(self.processed_chemicals)}")
            print(f"New Relationships This Session: {len(self.created_relationships)}")
        
        print("\n" + "="*100)
        print("PROCESSING COMPLETE")
        print("="*100)


def main():
    """Main execution function."""
    print("Starting P&ID Chemical Processing System")
    print("="*60)
    
    # Initialize processor
    processor = PIDChemicalProcessor(
        config.NEO4J_URI,
        config.NEO4J_USERNAME,
        config.NEO4J_PASSWORD
    )
    
    try:
        # Step 1: Find boundary nodes in P&ID
        boundaries = processor.find_boundary_nodes()
        
        if boundaries:
            # Step 2: Create chemical nodes and relationships
            processor.create_chemical_nodes_and_relationships(boundaries)
            
            # Step 3: Process MSDS files for detailed properties
            if hasattr(config, 'MSDS_DIRECTORY_PATH') and os.path.exists(config.MSDS_DIRECTORY_PATH):
                processor.process_msds_files(config.MSDS_DIRECTORY_PATH)
            else:
                print("MSDS directory not configured or not found. Skipping MSDS processing.")
            
            # Step 4: Generate final comprehensive report
            processor.generate_final_report()
        else:
            print("No boundary nodes found in the database.")
    
    except Exception as e:
        print(f"An error occurred during processing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        processor.close()


if __name__ == "__main__":
    main()