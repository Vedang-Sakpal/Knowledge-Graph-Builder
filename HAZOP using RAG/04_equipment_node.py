"""
Storage Tank P&ID Analysis with Ontology Integration

This script identifies storage tanks from a Neo4j P&ID database and generates
detailed process descriptions by combining graph data with ontology knowledge.
"""

import logging
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Any

# Third-party imports
try:
    from neo4j import GraphDatabase, basic_auth
    from rdflib import Graph, URIRef
    from rdflib.namespace import RDF, RDFS, OWL
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Please install: pip install neo4j rdflib")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tank_analysis.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class Connection:
    """Represents a connection between components in the P&ID"""
    source_equipment: str
    source_type: str
    target_equipment: str
    target_type: str
    connection_type: str
    pipeline_name: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    # ADDED: Node IDs to enable graph traversal for true endpoint resolution
    source_id: int | None = None
    target_id: int | None = None


# ADDED: Dataclass to represent a control loop
@dataclass(frozen=True) # Use frozen=True to make instances hashable for use in sets
class ControlLoop:
    """Represents a control loop associated with a tank."""
    sensor_name: str
    sensor_type: str
    controller_name: str
    controller_type: str
    actuator_name: str
    actuator_type: str
    description: str  # The 'name' property from the CONTROLS relationship


# MODIFIED: StorageTank dataclass to include control loops
@dataclass
class RoofSystem:
    """Represents a storage tank roof system"""
    type: str  # Fixed or Floating
    properties: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

@dataclass
class InstrumentSystem:
    """Represents an instrument or sensor in the storage tank"""
    name: str
    instrument_type: str
    measured_parameter: str
    location: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SafetySystem:
    """Represents a safety system component"""
    name: str
    system_type: str
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UtilitySystem:
    """Represents a utility system connected to the tank"""
    name: str
    utility_type: str
    supply_line: str
    destination: str  # e.g., "Jacket" or "Blanket Gas System"
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProcessParameter:
    """Represents a process parameter being monitored or controlled"""
    name: str
    parameter_type: str
    measurement_unit: str = ""
    normal_range: Dict[str, float] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StorageTank:
    """Represents a storage tank with all its properties and connections"""
    name: str
    node_id: str
    tank_type: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Core components
    inlets: List[Connection] = field(default_factory=list)
    outlets: List[Connection] = field(default_factory=list)
    roof_system: RoofSystem = field(default_factory=lambda: RoofSystem(""))
    
    # Systems and Instruments
    safety_systems: List[SafetySystem] = field(default_factory=list)
    instruments: List[InstrumentSystem] = field(default_factory=list)
    utilities: List[UtilitySystem] = field(default_factory=list)
    control_loops: List[ControlLoop] = field(default_factory=list)
    
    # Process Parameters
    monitored_parameters: List[ProcessParameter] = field(default_factory=list)


@dataclass
class OntologyKnowledge:
    """Stores extracted ontology knowledge about storage tanks with comprehensive mapping"""
    # Core Tank Classifications
    tank_classes: Dict[str, str] = field(default_factory=dict)
    tank_properties: Dict[str, Any] = field(default_factory=dict)
    
    # Process Connection Mappings
    process_connections: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    inflow_types: Dict[str, str] = field(default_factory=dict)
    outflow_types: Dict[str, str] = field(default_factory=dict)
    
    # Auxiliary Systems
    auxiliary_systems: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    utility_connections: Dict[str, str] = field(default_factory=dict)
    
    # Instrumentation & Control
    instrument_types: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    control_loops: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    measurement_parameters: Dict[str, str] = field(default_factory=dict)
    
    # Internal Components
    internal_components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    roof_types: Dict[str, str] = field(default_factory=dict)
    
    # Safety Systems
    safety_systems: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    safety_devices: Dict[str, str] = field(default_factory=dict)
    safety_concepts: Dict[str, str] = field(default_factory=dict)  # Added missing field
    
    # Process Parameters
    process_parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    parameter_relationships: Dict[str, List[str]] = field(default_factory=dict)  # Changed from list to dict
    process_concepts: Dict[str, str] = field(default_factory=dict)  # Added missing field
    
    # Equipment Connections
    equipment_connections: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    connection_types: Dict[str, str] = field(default_factory=dict)
    
    # Object Properties (Relationships)
    object_properties: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)


class OntologyParser:
    """Parser for Storage Tank Ontology RDF"""
    
    def __init__(self, ontology_path: str):
        """Initialize the ontology parser with the path to the RDF file
        
        Args:
            ontology_path (str): Path to the Storage Tank ontology RDF file
        """
        self.graph = Graph()
        self.ontology_path = ontology_path
        self.base_uri = "http://www.semanticweb.org/a/ontologies/2025/8/Storage_Tank_ontology#"
        self.knowledge = OntologyKnowledge()
        
    def load_ontology(self) -> None:
        """Load and parse the ontology file"""
        try:
            self.graph.parse(self.ontology_path, format="xml")
            logger.info(f"Successfully loaded ontology from {self.ontology_path}")
        except Exception as e:
            logger.error(f"Failed to load ontology: {e}")
            raise
    
    def extract_knowledge(self) -> OntologyKnowledge:
        """Extract all relevant knowledge from the ontology into structured format
        
        Returns:
            OntologyKnowledge: Populated knowledge structure
        """
        try:
            # Extract classes and their hierarchies
            self._extract_tank_classes()
            self._extract_process_connections()
            self._extract_auxiliary_systems()
            self._extract_instrumentation()
            self._extract_internal_components()
            self._extract_safety_systems()
            self._extract_parameters()
            self._extract_object_properties()
            
            # Extract concepts for safety and process
            for subject in self.graph.subjects(RDF.type, OWL.Class):
                class_name = str(subject).split('#')[-1]
                comments = list(self.graph.objects(subject, RDFS.comment))
                description = str(comments[0]) if comments else ""
                
                # Categorize based on name and content
                if any(term in class_name.lower() for term in ['safety', 'relief', 'protection', 'emergency']):
                    self.knowledge.safety_concepts[class_name] = description
                elif any(term in class_name.lower() for term in ['process', 'flow', 'operation']):
                    self.knowledge.process_concepts[class_name] = description
            
            return self.knowledge
            
        except Exception as e:
            logger.error(f"Error extracting ontology knowledge: {e}")
            # Initialize empty data structures to prevent attribute errors
            self.knowledge.safety_concepts = {}
            self.knowledge.process_concepts = {}
            return self.knowledge
    
    def _extract_tank_classes(self) -> None:
        """Extract storage tank classes and their properties"""
        tank_class = URIRef(self.base_uri + "Storage_tank")
        
        # Get all subclasses and their descriptions
        for subclass in self.graph.subjects(RDF.type, OWL.Class):
            if self.graph.value(subclass, RDFS.subClassOf) == tank_class:
                class_name = str(subclass).split("#")[-1]
                description = str(self.graph.value(subclass, RDFS.comment) or "")
                self.knowledge.tank_classes[class_name] = description
                
        # Extract tank properties
        for prop in self.graph.subjects(RDF.type, OWL.DatatypeProperty):
            if self.graph.value(prop, RDFS.domain) == tank_class:
                prop_name = str(prop).split("#")[-1]
                prop_type = str(self.graph.value(prop, RDFS.range))
                self.knowledge.tank_properties[prop_name] = prop_type

    def _extract_process_connections(self) -> None:
        """Extract knowledge about process connections"""
        for conn_type in self.graph.subjects(RDF.type, OWL.ObjectProperty):
            if "Process_Connection" in str(conn_type):
                conn_name = str(conn_type).split("#")[-1]
                domain = str(self.graph.value(conn_type, RDFS.domain) or "")
                range_ = str(self.graph.value(conn_type, RDFS.range) or "")
                self.knowledge.process_connections[conn_name] = {
                    "domain": domain,
                    "range": range_
                }

    def _extract_auxiliary_systems(self) -> None:
        """Extract auxiliary systems knowledge"""
        aux_class = URIRef(self.base_uri + "Auxiliary_System")
        for system in self.graph.subjects(RDFS.subClassOf, aux_class):
            system_name = str(system).split("#")[-1]
            description = str(self.graph.value(system, RDFS.comment) or "")
            self.knowledge.auxiliary_systems[system_name] = {
                "description": description,
                "connections": []
            }
            
    def _extract_instrumentation(self) -> None:
        """Extract instrumentation and control system knowledge"""
        instr_class = URIRef(self.base_uri + "Measuring_Instruments/Sensors")
        for instrument in self.graph.subjects(RDFS.subClassOf, instr_class):
            instr_name = str(instrument).split("#")[-1]
            description = str(self.graph.value(instrument, RDFS.comment) or "")
            measures = []
            for obj in self.graph.objects(instrument, URIRef(self.base_uri + "Measures")):
                measures.append(str(obj).split("#")[-1])
            self.knowledge.instrument_types[instr_name] = {
                "description": description,
                "measures": measures
            }

    def _extract_object_properties(self) -> None:
        """Extract object properties (relationships) from the ontology"""
        for prop in self.graph.subjects(RDF.type, OWL.ObjectProperty):
            prop_name = str(prop).split("#")[-1]
            domain = str(self.graph.value(prop, RDFS.domain) or "")
            range_ = str(self.graph.value(prop, RDFS.range) or "")
            self.knowledge.object_properties[prop_name] = {
                "domain": [domain],
                "range": [range_]
            }


class OntologyPIDMapper:
    """Maps P&ID elements to ontology concepts and generates descriptions"""
    
    def __init__(self, ontology_knowledge: OntologyKnowledge):
        """Initialize mapper with ontology knowledge
        
        Args:
            ontology_knowledge (OntologyKnowledge): Parsed ontology knowledge
        """
        self.knowledge = ontology_knowledge
        
    def map_storage_tank(self, tank: StorageTank) -> Dict[str, Any]:
        """Map storage tank and its components to ontology concepts
        
        Args:
            tank (StorageTank): Storage tank to map
            
        Returns:
            Dict[str, Any]: Structured mapping of tank components to ontology concepts
        """
        mapping = {
            "core_attributes": self._map_tank_attributes(tank),
            "process_connections": self._map_process_connections(tank),
            "instrumentation": self._map_instrumentation(tank),
            "safety_systems": self._map_safety_systems(tank),
            "utilities": self._map_utility_systems(tank),
            "parameters": self._map_process_parameters(tank)
        }
        return mapping
    
    def generate_description(self, tank: StorageTank) -> str:
        """Generate a detailed description of the storage tank based on ontology mapping
        
        Args:
            tank (StorageTank): Storage tank to describe
            
        Returns:
            str: Structured description of the tank and its systems
        """
        mapping = self.map_storage_tank(tank)
        
        # Build description sections
        sections = []
        
        # Core description
        core = mapping["core_attributes"]
        sections.append(f"Storage Tank {tank.name} Description:\n")
        sections.append(f"Type: {core['tank_type']}")
        sections.append(f"Material: {core.get('material', 'Not specified')}")
        sections.append(f"Volume: {core.get('volume', 'Not specified')} m³")
        
        # Process connections
        sections.append("\nProcess Connections:")
        for conn in mapping["process_connections"]:
            sections.append(f"- {conn['description']}")
        
        # Instrumentation
        sections.append("\nInstrumentation and Control:")
        for inst in mapping["instrumentation"]:
            sections.append(f"- {inst['name']}: {inst['description']}")
        
        # Safety systems
        if mapping["safety_systems"]:
            sections.append("\nSafety Systems:")
            for system in mapping["safety_systems"]:
                sections.append(f"- {system['name']}: {system['description']}")
        
        # Utilities
        if mapping["utilities"]:
            sections.append("\nUtility Systems:")
            for utility in mapping["utilities"]:
                sections.append(f"- {utility['name']}: {utility['description']}")
        
        # Parameters
        sections.append("\nMonitored Parameters:")
        for param in mapping["parameters"]:
            sections.append(f"- {param['name']}: {param['description']}")
        
        return "\n".join(sections)
    
    def _map_tank_attributes(self, tank: StorageTank) -> Dict[str, Any]:
        """Map core tank attributes to ontology concepts"""
        attributes = {}
        
        # Map tank type
        if tank.tank_type in self.knowledge.tank_classes:
            attributes["tank_type"] = tank.tank_type
            attributes["type_description"] = self.knowledge.tank_classes[tank.tank_type]
        
        # Map properties
        for prop_name, prop_value in tank.properties.items():
            if prop_name in self.knowledge.tank_properties:
                attributes[prop_name] = prop_value
        
        return attributes
    
    def _map_process_connections(self, tank: StorageTank) -> List[Dict[str, Any]]:
        """Map process connections to ontology concepts"""
        connections = []
        
        # Map inlets
        for inlet in tank.inlets:
            if inlet.connection_type in self.knowledge.process_connections:
                conn_info = self.knowledge.process_connections[inlet.connection_type]
                connections.append({
                    "type": "inlet",
                    "description": f"Inlet from {inlet.source_equipment} via {inlet.pipeline_name}",
                    "ontology_mapping": conn_info
                })
        
        # Map outlets
        for outlet in tank.outlets:
            if outlet.connection_type in self.knowledge.process_connections:
                conn_info = self.knowledge.process_connections[outlet.connection_type]
                connections.append({
                    "type": "outlet",
                    "description": f"Outlet to {outlet.target_equipment} via {outlet.pipeline_name}",
                    "ontology_mapping": conn_info
                })
        
        return connections
    
    def _map_instrumentation(self, tank: StorageTank) -> List[Dict[str, Any]]:
        """Map instrumentation to ontology concepts"""
        instrumentation = []
        
        # Map instruments
        for instrument in tank.instruments:
            if instrument.instrument_type in self.knowledge.instrument_types:
                inst_info = self.knowledge.instrument_types[instrument.instrument_type]
                instrumentation.append({
                    "name": instrument.name,
                    "type": instrument.instrument_type,
                    "description": inst_info.get("description", ""),
                    "measures": inst_info.get("measures", [])
                })
        
        return instrumentation
    
    def _map_safety_systems(self, tank: StorageTank) -> List[Dict[str, Any]]:
        """Map safety systems to ontology concepts"""
        safety_systems = []
        
        for system in tank.safety_systems:
            if system.system_type in self.knowledge.safety_systems:
                sys_info = self.knowledge.safety_systems[system.system_type]
                safety_systems.append({
                    "name": system.name,
                    "type": system.system_type,
                    "description": sys_info.get("description", "")
                })
        
        return safety_systems
    
    def _map_utility_systems(self, tank: StorageTank) -> List[Dict[str, Any]]:
        """Map utility systems to ontology concepts"""
        utilities = []
        
        for utility in tank.utilities:
            if utility.utility_type in self.knowledge.auxiliary_systems:
                # util_info = self.knowledge.auxiliary_systems[utility.utility_type]
                utilities.append({
                    "name": utility.name,
                    "type": utility.utility_type,
                    "description": f"{utility.utility_type} supplied to {utility.destination}"
                })
        
        return utilities
    
    def _map_process_parameters(self, tank: StorageTank) -> List[Dict[str, Any]]:
        """Map process parameters to ontology concepts"""
        parameters = []
        
        for param in tank.monitored_parameters:
            if param.parameter_type in self.knowledge.process_parameters:
                param_info = self.knowledge.process_parameters[param.parameter_type]
                parameters.append({
                    "name": param.name,
                    "type": param.parameter_type,
                    "description": param_info.get("description", ""),
                    "unit": param.measurement_unit,
                    "normal_range": param.normal_range
                })
        
        return parameters


class Neo4jConnector:
    """Handles connection and queries to Neo4j database"""

    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None

    def connect(self) -> bool:
        """Establish connection to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=basic_auth(self.user, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Successfully connected to Neo4j at {self.uri}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False

    def close(self):
        """Close the database connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def get_all_nodes_and_relationships(self) -> tuple[List[Dict], List[Dict]]:
        """Extract all nodes and relationships from the database"""
        nodes = []
        relationships = []

        try:
            with self.driver.session() as session:
                # Get all nodes
                node_query = """
                MATCH (n)
                RETURN id(n) as node_id, labels(n) as labels, properties(n) as properties
                """
                node_result = session.run(node_query)
                for record in node_result:
                    nodes.append({
                        'id': record['node_id'],
                        'labels': record['labels'],
                        'properties': record['properties']
                    })

                # Get all relationships
                rel_query = """
                MATCH (a)-[r]->(b)
                RETURN id(a) as source_id, id(b) as target_id,
                       type(r) as relationship_type, properties(r) as properties,
                       labels(a) as source_labels, properties(a) as source_props,
                       labels(b) as target_labels, properties(b) as target_props
                """
                # CHANGED: Added labels to the query to help with categorization
                rel_result = session.run(rel_query)
                for record in rel_result:
                    relationships.append({
                        'source_id': record['source_id'],
                        'target_id': record['target_id'],
                        'type': record['relationship_type'],
                        'properties': record['properties'],
                        'source_labels': record['source_labels'],
                        'source_props': record['source_props'],
                        'target_labels': record['target_labels'],
                        'target_props': record['target_props']
                    })

                logger.info(f"Extracted {len(nodes)} nodes and {len(relationships)} relationships")
                return nodes, relationships

        except Exception as e:
            logger.error(f"Error querying Neo4j database: {e}")
            return [], []

    # CHANGED: This entire function is replaced with a working implementation.
    def backtrack_chemicals(self, tank_name: str, direction: str = 'upstream') -> List[Dict]:
        """Backtrack chemicals through pipes for a given tank across common flow relationships."""

        # Allow multiple common flow relationship types and cap traversal depth
        # Note: In Cypher, alternate relationship types in variable-length paths must be like :A|B|C
        flow_rels = "CONNECTED_TO|FLOWS_TO|FLOW_TO|FLOWS|CONNECTS_TO"

        if direction == 'upstream':
            query = f"""
            MATCH (tank:Equipment {{name: $tank_name}})
            MATCH path = (src:Boundary)-[:{flow_rels}*1..10]->(tank)
            WHERE toLower(src.type) = 'source'
            OPTIONAL MATCH (chem:Chemical)-[:Inlet]->(src)
            RETURN DISTINCT
                chem.name AS chemical,
                [node IN nodes(path) | node.name] AS path_nodes,
                [rel IN relationships(path) | coalesce(rel.name, type(rel))] AS path_pipelines
            ORDER BY chemical
            LIMIT 50
            """
        else:  # downstream
            query = f"""
            MATCH (tank:Equipment {{name: $tank_name}})
            MATCH path = (tank)-[:{flow_rels}*1..10]->(sink:Boundary)
            WHERE toLower(sink.type) = 'sink'
            OPTIONAL MATCH (chem:Chemical)<-[:Outlet]-(sink)
            RETURN DISTINCT
                chem.name AS chemical,
                [node IN nodes(path) | node.name] AS path_nodes,
                [rel IN relationships(path) | coalesce(rel.name, type(rel))] AS path_pipelines
            ORDER BY chemical
            LIMIT 50
            """
        try:
            with self.driver.session() as session:
                result = session.run(query, tank_name=tank_name)
                paths = [dict(record) for record in result]
                return paths
        except Exception as e:
            logger.error(f"Error backtracking chemicals for {tank_name}: {e}")
            return []

class StorageTankAnalyzer:
    """Analyzes storage tanks and generates process descriptions"""

    def __init__(self):
        self.node_lookup: Dict[int, Dict] = {}
        # ADDED: adjacency maps for upstream/downstream traversal
        self._incoming_edges: Dict[int, List[int]] = {}
        self._outgoing_edges: Dict[int, List[int]] = {}

    def identify_storage_tanks(self, nodes: List[Dict]) -> List[StorageTank]:
        """Identify storage tank nodes using type property containing 'Storage Tank'"""
        tanks = []

        # Create node lookup for quick access
        self.node_lookup = {node['id']: node for node in nodes}

        for node in nodes:
            props = node.get('properties', {})
            node_type = props.get('type', '').lower() # Use lower for case-insensitive match

            # Check if type property contains "storage tank"
            if 'storage tank' in node_type:
                tank = StorageTank(
                    name=props.get('name', f"Tank_{node['id']}"),
                    node_id=str(node['id']),
                    tank_type=props.get('type', ''),
                    properties=props
                )
                tanks.append(tank)
                logger.info(f"Identified storage tank: {tank.name}")

        return tanks

    # MODIFIED: This function now orchestrates control loop analysis as well
    def analyze_connections(self, tanks: List[StorageTank], relationships: List[Dict]):
        """Analyze connections for each storage tank and identify control loops."""

        tank_ids = {int(tank.node_id) for tank in tanks}
        tank_by_id = {int(tank.node_id): tank for tank in tanks}

        # ADDED: Build adjacency maps for traversal
        self._incoming_edges = {}
        self._outgoing_edges = {}
        for rel in relationships:
            src = rel['source_id']
            tgt = rel['target_id']
            self._outgoing_edges.setdefault(src, []).append(tgt)
            self._incoming_edges.setdefault(tgt, []).append(src)

        for rel in relationships:
            source_id = rel['source_id']
            target_id = rel['target_id']
            rel_type = rel['type']
            rel_props = rel.get('properties', {})

            tank = None
            connection_direction = None
            other_node_id = None

            if source_id in tank_ids:
                tank = tank_by_id[source_id]
                connection_direction = 'outgoing'
                other_node_id = target_id
            elif target_id in tank_ids:
                tank = tank_by_id[target_id]
                connection_direction = 'incoming'
                other_node_id = source_id

            if not tank:
                continue

            other_node = self.node_lookup.get(other_node_id, {})
            other_props = other_node.get('properties', {})
            other_name = other_props.get('name', f"Node_{other_node_id}")
            other_type = other_props.get('type', 'Unknown')

            # ADDED: Get labels of the other node to help categorization
            other_labels = other_node.get('labels', [])

            pipeline_name = rel_props.get('name', '')

            connection = Connection(
                source_equipment=other_name if connection_direction == 'incoming' else tank.name,
                source_type=other_type if connection_direction == 'incoming' else tank.tank_type,
                target_equipment=tank.name if connection_direction == 'incoming' else other_name,
                target_type=tank.tank_type if connection_direction == 'incoming' else other_type,
                connection_type=rel_type,
                pipeline_name=pipeline_name,
                properties=rel_props,
                source_id=other_node_id if connection_direction == 'incoming' else int(tank.node_id),
                target_id=int(tank.node_id) if connection_direction == 'incoming' else other_node_id
            )

            # CHANGED: Pass more info to the categorization function
            self._categorize_connection(tank, connection, other_type, other_labels, connection_direction)

        # ADDED: Call the control loop analysis after all direct connections are processed
        self._analyze_control_loops(tanks, relationships)

    # ADDED: New private method to find and associate control loops
    def _analyze_control_loops(self, tanks: List[StorageTank], relationships: List[Dict]):
        """Identifies control loops from the graph data and associates them with the relevant tank."""
        logger.info("Analyzing P&ID data to infer control loops based on ontology logic.")
        # Build maps for quick lookups of control relationships
        sensor_to_controller = {} # Maps {sensor_id: (controller_id, signal_name)}
        controller_to_actuator = {} # Maps {controller_id: (actuator_id, control_desc)}

        for rel in relationships:
            rel_type = rel.get('type', '').upper()
            if rel_type == 'SEND_SIGNAL_TO':
                sensor_id = rel['source_id']
                controller_id = rel['target_id']
                signal_name = rel.get('properties', {}).get('name', 'a signal')
                sensor_to_controller[sensor_id] = (controller_id, signal_name)
            elif rel_type == 'CONTROLS':
                controller_id = rel['source_id']
                actuator_id = rel['target_id']
                control_desc = rel.get('properties', {}).get('name', 'controls the actuator')
                controller_to_actuator[controller_id] = (actuator_id, control_desc)

        # Associate loops with tanks by checking if the sensor is one of the tank's instruments
        for tank in tanks:
            # Get IDs of all instruments directly connected to the tank
            tank_instruments_ids = {
                int(conn.target_id) if conn.source_equipment == tank.name else int(conn.source_id)
                for conn in tank.instruments
            }

            for inst_id in tank_instruments_ids:
                if inst_id in sensor_to_controller:
                    controller_id, _ = sensor_to_controller[inst_id]
                    if controller_id in controller_to_actuator:
                        actuator_id, control_desc = controller_to_actuator[controller_id]

                        # We found a complete loop: Sensor -> Controller -> Actuator
                        sensor_node = self.node_lookup.get(inst_id, {})
                        controller_node = self.node_lookup.get(controller_id, {})
                        actuator_node = self.node_lookup.get(actuator_id, {})

                        # Skip if any node data is missing from our lookup
                        if not all([sensor_node, controller_node, actuator_node]):
                            continue

                        loop = ControlLoop(
                            sensor_name=sensor_node.get('properties', {}).get('name', f"Sensor_{inst_id}"),
                            sensor_type=sensor_node.get('properties', {}).get('type', 'Unknown Sensor'),
                            controller_name=controller_node.get('properties', {}).get('name', f"Controller_{controller_id}"),
                            controller_type=controller_node.get('properties', {}).get('type', 'Unknown Controller'),
                            actuator_name=actuator_node.get('properties', {}).get('name', f"Actuator_{actuator_id}"),
                            actuator_type=actuator_node.get('properties', {}).get('type', 'Unknown Actuator'),
                            description=control_desc
                        )
                        # Avoid adding duplicate loops
                        if loop not in tank.control_loops:
                            tank.control_loops.append(loop)
                            logger.info(f"Identified control loop for tank {tank.name}: {loop.sensor_name} -> {loop.controller_name} -> {loop.actuator_name}")


    # CHANGED: This categorization logic is revised to handle multiple flow relationship types.
    def _categorize_connection(self, tank: StorageTank, connection: Connection,
                             other_type: str, other_labels: List[str], direction: str):
        """Categorize connections into inlets, outlets, safety, instruments, or utilities."""

        normalized_rel = connection.connection_type.upper().replace(" ", "_")
        physical_relationships = {"CONNECTED_TO", "FLOWS_TO", "FLOW_TO", "FLOWS", "CONNECTS_TO"}

        # Instrumentation/control relationships are non-physical
        instrumentation_relationships = {"HAS_INSTRUMENT", "SEND_SIGNAL_TO", "CONTROLS", "MEASURES"}
        if normalized_rel in instrumentation_relationships:
            tank.instruments.append(connection)
            return

        # If it's not in known physical set, treat heuristically: if other node is Sensor/Controller, mark as instrument
        if normalized_rel not in physical_relationships:
            if any(label in other_labels for label in ['Sensor', 'Controller', 'Instrument']):
                tank.instruments.append(connection)
            else:
                # Default to process stream to avoid missing flows in varied schemas
                if direction == 'incoming':
                    tank.inlets.append(connection)
                else:
                    tank.outlets.append(connection)
            return

        # Physical connection: determine category by other equipment type
        other_type_lower = other_type.lower()

        # Safety systems (e.g., Pressure Relief Valve)
        if any(term in other_type_lower for term in ['relief', 'safety', 'emergency', 'rupture']):
            tank.safety_systems.append(connection)
            return

        # Utilities (e.g., Steam, Nitrogen)
        if any(term in other_type_lower for term in ['steam', 'nitrogen', 'utility']):
            tank.utilities.append(connection)
            return

        # Sensors/Controllers/Valves: also list as instruments for completeness
        if any(label in other_labels for label in ['Sensor', 'Controller', 'Valve', 'Instrument']):
            tank.instruments.append(connection)

        # Process streams: classify as inlet or outlet
        if direction == 'incoming':
            tank.inlets.append(connection)
        else:
            tank.outlets.append(connection)


    def generate_descriptions(self, tanks: List[StorageTank], knowledge: OntologyKnowledge, neo4j_conn: Neo4jConnector) -> str:
        """Generate comprehensive process descriptions including chemical tracking"""

        sections = []

        sections.append("STORAGE TANK PROCESS DESCRIPTIONS")
        sections.append("=" * 50)
        sections.append("Generated from P&ID Database Analysis")
        sections.append(f"Total Storage Tanks Analyzed: {len(tanks)}")
        sections.append("=" * 50)
        sections.append("")

        for tank in tanks:
            tank_description = self._generate_tank_description(tank, knowledge, neo4j_conn)
            sections.append(tank_description)
            sections.append("")

        return "\n".join(sections)

    def _generate_tank_description(self, tank: StorageTank, knowledge: OntologyKnowledge, neo4j_conn: Neo4jConnector) -> str:
        """Generate description including chemical backtracking"""

        lines = []

        lines.append(f"=== STORAGE TANK ANALYSIS: {tank.name} ===")
        lines.append("")

        lines.append("BASIC INFORMATION:")
        lines.append(f"Tank Name: {tank.name}")
        lines.append(f"Tank Type: {tank.tank_type}")
        lines.append(f"Node ID: {tank.node_id}")

        if tank.properties:
            lines.append("")
            lines.append("TANK PROPERTIES:")
            for prop, value in tank.properties.items():
                if prop not in ['name', 'type']:
                    lines.append(f"  {prop.replace('_', ' ').title()}: {value}")

        lines.extend(self._get_ontology_description(knowledge))
        lines.extend(self._describe_process_function(tank, knowledge))
        # Get upstream data first before using it
        upstream_data = neo4j_conn.backtrack_chemicals(tank.name, direction='upstream')

        if tank.inlets:
            lines.extend(self._describe_inlets(tank, upstream_data))
        else:
            lines.append("")
            lines.append("INLET STREAMS:")
            lines.append("  None identified")
        # Get downstream data before using it
        downstream_data = neo4j_conn.backtrack_chemicals(tank.name, direction='downstream')

        if tank.outlets:
            lines.extend(self._describe_outlets(tank, downstream_data))
        else:
            lines.append("")
            lines.append("OUTLET STREAMS:")
            lines.append("  None identified")

        if tank.safety_systems:
            lines.extend(self._describe_safety_systems(tank, tank.safety_systems, knowledge))

        if tank.instruments:
            lines.extend(self._describe_instrumentation(tank, tank.instruments))

        if tank.utilities:
            lines.extend(self._describe_utilities(tank.utilities))

        # ADDED: Call the backtracking function here to use its results multiple times.
        upstream_data = neo4j_conn.backtrack_chemicals(tank.name, direction='upstream')
        downstream_data = neo4j_conn.backtrack_chemicals(tank.name, direction='downstream')

        # CHANGED: This section now infers chemicals from the upstream backtracking result.
        lines.append("")
        lines.append("CHEMICALS IN TANK (INFERRED FROM INLETS):")
        if upstream_data:
            unique_chemicals = {item['chemical'] for item in upstream_data if item['chemical']}
            if unique_chemicals:
                for chem in sorted(list(unique_chemicals)):
                    lines.append(f"  • {chem}")
            else:
                 lines.append("  No specific chemical source found upstream.")
        else:
            lines.append("  No upstream chemical source found to infer tank contents.")

        # CHANGED: This section now prints the full flow path and associated chemical.
        lines.append("")
        lines.append("UPSTREAM PROCESS FLOW AND CHEMICALS:")
        if upstream_data:
            for item in upstream_data:
                # Combine nodes and pipelines for a clear path description
                path_segments = []
                for i, node_name in enumerate(item['path_nodes']):
                    path_segments.append(node_name)
                    if i < len(item['path_pipelines']):
                        path_segments.append(f"-[{item['path_pipelines'][i]}]->")
                path_str = " ".join(path_segments)

                lines.append(f"  • Chemical '{item['chemical']}' originates from:")
                lines.append(f"    PATH: {path_str}")
        else:
            lines.append("  No chemical information found upstream.")

        # CHANGED: This section is updated to match the upstream section's formatting.
        lines.append("")
        lines.append("DOWNSTREAM PROCESS FLOW AND CHEMICALS:")
        if downstream_data:
            for item in downstream_data:
                path_segments = []
                for i, node_name in enumerate(item['path_nodes']):
                    path_segments.append(node_name)
                    if i < len(item['path_pipelines']):
                        path_segments.append(f"-[{item['path_pipelines'][i]}]->")
                path_str = " ".join(path_segments)

                lines.append(f"  • Contents are sent to sink '{item['path_nodes'][-1]}' which contains '{item['chemical']}':")
                lines.append(f"    PATH: {path_str}")
        else:
            lines.append("  No chemical information found downstream.")

        lines.extend(self._describe_integration(tank, upstream_data, downstream_data))

        lines.append("=" * 60)

        return "\n".join(lines)

    def _get_ontology_description(self, knowledge: OntologyKnowledge) -> List[str]:
        """Get ontology-based tank description"""
        lines = ["", "ONTOLOGY CLASSIFICATION:"]

        storage_desc = knowledge.tank_classes.get('Storage_tank',
            'Storage tanks serve as buffer vessels in process plants, enabling '
            'continuous operation by decoupling flow rates between process units.')

        lines.append("According to the storage tank ontology:")
        lines.append(f"  {storage_desc}")

        return lines

    def _describe_process_function(self, tank: StorageTank, knowledge: OntologyKnowledge) -> List[str]:
        """Describe the tank's process function"""
        lines = ["", "PROCESS FUNCTION:"]

        if len(tank.inlets) == 1 and len(tank.outlets) == 1:
            lines.append("This tank operates as a surge vessel, providing buffering between")
            lines.append("upstream equipment and downstream processing units.")
        elif len(tank.inlets) > 1:
            lines.append("This tank serves as a collection/mixing vessel, receiving")
            lines.append("streams from multiple upstream sources.")
        elif len(tank.outlets) > 1:
            lines.append("This tank functions as a distribution vessel, supplying")
            lines.append("multiple downstream process units.")
        else:
            lines.append("This tank provides storage capacity and process buffering.")

        return lines

    def _describe_inlets(self, tank: StorageTank, upstream_data: List[Dict]) -> List[str]:
        """Describe inlet streams using nearest upstream Equipment or Boundary from path data"""
        lines = ["", "INLET STREAMS:"]

        # Build a map from the tank's immediate neighbor to the actual upstream equipment/boundary
        neighbor_to_endpoint: Dict[str, str] = {}
        if upstream_data:
            for item in upstream_data:
                path_nodes = item.get('path_nodes') or []
                if len(path_nodes) < 2:
                    continue

                # The immediate neighbor is the node right before the tank in the path
                neighbor = path_nodes[-2]
                endpoint = None

                # Walk backward from the neighbor to find the first "significant" node
                for node_name in reversed(path_nodes[:-1]):
                    name_lower = (node_name or '').lower()
                    # Skip over common fittings and non-descriptive components
                    if any(k in name_lower for k in ['flange', 'joint', 'reducer', 'strainer', 'vent', 'mounting', 'piping', 'y-type', 'tp-']):
                        continue

                    # The first node that is not a fitting is our endpoint
                    endpoint = node_name
                    break

                # Fallback to the very first node in the path (the Boundary) if no other equipment is found
                if not endpoint and path_nodes:
                    endpoint = path_nodes[0]

                if endpoint:
                    neighbor_to_endpoint[neighbor] = endpoint

        # Generate the description, preferring nearest Equipment by label
        for i, conn in enumerate(tank.inlets, 1):
            # First: traverse to nearest node labeled Equipment
            display_from = self._resolve_nearest_labeled(conn.source_id, direction='upstream', required_label='Equipment')
            if not display_from:
                # Next: use neighbor mapping from path analysis
                display_from = neighbor_to_endpoint.get(conn.source_equipment, None)
            if not display_from:
                # Fallback: nearest significant (Equipment or Boundary)
                display_from = self._resolve_true_endpoint(conn.source_id, direction='upstream') or conn.source_equipment
            lines.append(f"  {i}. FROM: {display_from}")
            lines.append(f"     TO: {tank.name}")
            lines.append(f"     Connection Type: {conn.connection_type}")
            if conn.pipeline_name:
                lines.append(f"     Pipeline: {conn.pipeline_name}")
            lines.append("")

        return lines

    def _describe_outlets(self, tank: StorageTank, downstream_data: List[Dict]) -> List[str]:
        """Describe outlet streams using nearest downstream Equipment or Boundary from path data"""
        lines = ["", "OUTLET STREAMS:"]

        # Build a map from the tank's immediate neighbor to the actual downstream equipment/boundary
        neighbor_to_endpoint: Dict[str, str] = {}
        if downstream_data:
            for item in downstream_data:
                path_nodes = item.get('path_nodes') or []
                if len(path_nodes) < 2:
                    continue

                # The immediate neighbor is the node right after the tank in the path
                neighbor = path_nodes[1]
                endpoint = None

                # Walk forward from the neighbor to find the first "significant" node
                for node_name in path_nodes[1:]:
                    name_lower = (node_name or '').lower()
                    # Skip over common fittings
                    if any(k in name_lower for k in ['flange', 'joint', 'reducer', 'strainer', 'vent', 'mounting', 'piping', 'y-type', 'tp-']):
                        continue

                    # The first node that is not a fitting is our endpoint
                    endpoint = node_name
                    break

                # Fallback to the very last node in the path (the Boundary sink)
                if not endpoint and path_nodes:
                    endpoint = path_nodes[-1]

                if endpoint:
                    neighbor_to_endpoint[neighbor] = endpoint

        # Generate the description, preferring nearest Equipment by label
        for i, conn in enumerate(tank.outlets, 1):
            # First: traverse to nearest node labeled Equipment
            display_to = self._resolve_nearest_labeled(conn.target_id, direction='downstream', required_label='Equipment')
            if not display_to:
                # Next: use neighbor mapping from path analysis
                display_to = neighbor_to_endpoint.get(conn.target_equipment, None)
            if not display_to:
                # Fallback: nearest significant (Equipment or Boundary)
                display_to = self._resolve_true_endpoint(conn.target_id, direction='downstream') or conn.target_equipment
            lines.append(f"  {i}. FROM: {tank.name}")
            lines.append(f"     TO: {display_to}")
            lines.append(f"     Connection Type: {conn.connection_type}")
            if conn.pipeline_name:
                lines.append(f"     Pipeline: {conn.pipeline_name}")
            lines.append("")

        return lines

    # ADDED: Helpers to resolve endpoints avoiding instruments and fittings
    def _resolve_true_endpoint(self, start_node_id: int | None, direction: str) -> str | None:
        """Traverse the graph from a neighbor node to find the nearest significant Equipment or Boundary.

        direction: 'upstream' uses incoming edges; 'downstream' uses outgoing edges.
        """
        if start_node_id is None:
            return None

        visited = set()
        frontier = [start_node_id]
        steps = 0
        max_steps = 12

        while frontier and steps < max_steps:
            next_frontier = []
            for node_id in frontier:
                if node_id in visited:
                    continue
                visited.add(node_id)

                if self._is_significant_node(node_id):
                    node = self.node_lookup.get(node_id, {})
                    props = node.get('properties', {})
                    return props.get('name') or f"Node_{node_id}"

                neighbors = []
                if direction == 'upstream':
                    neighbors = self._incoming_edges.get(node_id, [])
                else:
                    neighbors = self._outgoing_edges.get(node_id, [])
                for nb in neighbors:
                    if nb not in visited:
                        next_frontier.append(nb)
            frontier = next_frontier
            steps += 1
        return None

    def _resolve_nearest_labeled(self, start_node_id: int | None, direction: str, required_label: str) -> str | None:
        """Find nearest node whose labels include required_label (case-insensitive)."""
        if start_node_id is None:
            return None
        target = required_label.lower()
        visited = set()
        frontier = [start_node_id]
        steps = 0
        max_steps = 12
        while frontier and steps < max_steps:
            next_frontier = []
            for node_id in frontier:
                if node_id in visited:
                    continue
                visited.add(node_id)

                node = self.node_lookup.get(node_id, {})
                labels = [label.lower() for label in node.get('labels', [])]
                if target in labels:
                    props = node.get('properties', {})
                    return props.get('name') or f"Node_{node_id}"

                neighbors = self._incoming_edges.get(node_id, []) if direction == 'upstream' else self._outgoing_edges.get(node_id, [])
                for nb in neighbors:
                    if nb not in visited:
                        next_frontier.append(nb)
            frontier = next_frontier
            steps += 1
        return None

    def _is_significant_node(self, node_id: int) -> bool:
        """Return True if node is an Equipment or Boundary (not instrument or fitting)."""
        node = self.node_lookup.get(node_id, {})
        labels = [label.lower() for label in node.get('labels', [])]
        props = node.get('properties', {})
        node_type = (props.get('type') or '').lower()
        name_lower = (props.get('name') or '').lower()

        # Exclude obvious non-process equipment
        excluded_name_keywords = [
            'flange', 'joint', 'reducer', 'strainer', 'vent', 'mounting', 'piping', 'y-type', 'tp-'
        ]
        if any(k in name_lower for k in excluded_name_keywords):
            return False

        # Exclude by labels
        if any(lbl in labels for lbl in ['instrument', 'piping_and_fitting', 'sensor', 'controller']):
            return False

        # Exclude by type keywords
        excluded_type_keywords = ['valve', 'sensor', 'controller', 'indicator', 'transmitter', 'switch', 'fitting']
        if any(k in node_type for k in excluded_type_keywords):
            return False

        # Include if equipment or boundary
        if any(lbl in labels for lbl in ['equipment', 'boundary']):
            return True

        # As a fallback, treat nodes without excluded traits as significant
        return bool(props.get('name'))

    def _describe_safety_systems(self, tank: StorageTank, safety_systems: List[Connection],
                               knowledge: OntologyKnowledge) -> List[str]:
        """Describe safety systems"""
        lines = ["", "SAFETY SYSTEMS:"]

        for i, conn in enumerate(safety_systems, 1):
            # Show the device connected to the tank
            equipment_name = conn.target_equipment if conn.source_equipment == tank.name else conn.source_equipment
            equipment_type = conn.target_type if conn.source_equipment == tank.name else conn.source_type
            lines.append(f"  {i}. {equipment_name} ({equipment_type})")

            # Get description from ontology
            for safety_class, desc in knowledge.safety_concepts.items():
                if any(term in equipment_name.lower() for term in ['relief', 'safety']):
                    lines.append(f"     Function: {desc}")
                    break
            else:
                lines.append("     Function: Provides overpressure protection")

            lines.append("")

        return lines

    # MODIFIED: The instrumentation description now includes details about control loops
    def _describe_instrumentation(self, tank: StorageTank, instruments: List[Connection]) -> List[str]:
        """Describe instrumentation and control, including inferred control loops."""
        lines = ["", "INSTRUMENTATION & CONTROL:"]

        lines.append("This tank is equipped with the following instruments for monitoring and control:")
        # First, describe the individual instruments connected to the tank
        instrument_names = set()
        for conn in instruments:
            if conn.source_equipment == tank.name:
                equipment_name = conn.target_equipment
                equipment_type = conn.target_type
            else:
                equipment_name = conn.source_equipment
                equipment_type = conn.source_type
            
            # Avoid duplicate listing
            if equipment_name not in instrument_names:
                lines.append(f"  • {equipment_name} ({equipment_type})")
                instrument_names.add(equipment_name)
        lines.append("")

        # Now, describe the identified control loops in a separate, detailed section
        if tank.control_loops:
            lines.append("Inferred Control Loops based on Ontology Logic:")
            for loop in tank.control_loops:
                # Infer the parameter being controlled from the sensor's type property
                param_guess = "level" if "level" in loop.sensor_type.lower() else \
                              "flow" if "flow" in loop.sensor_type.lower() else \
                              "pressure" if "pressure" in loop.sensor_type.lower() else \
                              "temperature" if "temperature" in loop.sensor_type.lower() else \
                              "a process parameter"

                lines.append(f"  • A {param_guess} control loop is in place. Based on the P&ID connections,")
                lines.append(f"    the logic is as follows: The {loop.sensor_name} ({loop.sensor_type}) measures the {param_guess},")
                lines.append(f"    sends a signal to {loop.controller_name} ({loop.controller_type}), which then manipulates the")
                lines.append(f"    {loop.actuator_name} ({loop.actuator_type}) to maintain the desired setpoint.")
                lines.append(f"    (P&ID Control Logic: '{loop.description}')")
                lines.append("")

        return lines

    def _describe_utilities(self, utilities: List[Connection]) -> List[str]:
        """Describe utility connections"""
        lines = ["", "UTILITY CONNECTIONS:"]

        for i, conn in enumerate(utilities, 1):
            lines.append(f"  {i}. FROM: {conn.source_equipment}")
            lines.append(f"     TO: {conn.target_equipment}")
            lines.append(f"     Type: {conn.target_type}")
            lines.append("")

        return lines

    def _describe_integration(self, tank: StorageTank, upstream_data: List[Dict] = None, downstream_data: List[Dict] = None) -> List[str]:
        """Describe process integration"""
        lines = ["", "PROCESS INTEGRATION:"]

        # Use graph traversal to resolve true upstream Equipment by label (fallback to significant)
        upstream_equipment: set[str] = set()
        for conn in tank.inlets:
            resolved = self._resolve_nearest_labeled(conn.source_id, direction='upstream', required_label='Equipment')
            if not resolved:
                resolved = self._resolve_true_endpoint(conn.source_id, direction='upstream')
            if resolved:
                upstream_equipment.add(resolved)
        if upstream_equipment:
            lines.append("Upstream Integration: Receives material from:")
            for equipment in sorted(list(upstream_equipment)):
                lines.append(f"  • {equipment}")

        # Use graph traversal to resolve true downstream Equipment by label (fallback to significant)
        downstream_equipment: set[str] = set()
        for conn in tank.outlets:
            resolved = self._resolve_nearest_labeled(conn.target_id, direction='downstream', required_label='Equipment')
            if not resolved:
                resolved = self._resolve_true_endpoint(conn.target_id, direction='downstream')
            if resolved:
                downstream_equipment.add(resolved)
        if downstream_equipment:
            lines.append("Downstream Integration: Supplies material to:")
            for equipment in sorted(list(downstream_equipment)):
                lines.append(f"  • {equipment}")

        lines.append("")
        lines.append("This storage tank serves as a critical buffer in the process,")
        lines.append("enabling continuous operation and flow rate management.")

        return lines


def main():
    # Make sure to update these paths and credentials for your system
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "Ontocape@123" # CHANGED: Use your actual password
    ONTOLOGY_PATH = "Process description using ontology/Ontology/Storage Tank Ontology.rdf" # CHANGED: Assumes files are in same directory
    OUTPUT_PATH = "Process Description/generated_description.txt" # CHANGED: Assumes files are in same directory
    
    logger.info("Starting Storage Tank P&ID Analysis with Chemical Backtracking")

    neo4j_conn = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    ontology_parser = OntologyParser(ONTOLOGY_PATH)
    analyzer = StorageTankAnalyzer()

    try:
        if not neo4j_conn.connect():
            logger.error("Failed to connect to Neo4j. Exiting.")
            return

        nodes, relationships = neo4j_conn.get_all_nodes_and_relationships()

        if not nodes:
            logger.error("No data extracted from Neo4j.")
            return

        if not ontology_parser.load_ontology():
            logger.warning("Failed to load ontology. Using basic descriptions.")
            ontology_knowledge = OntologyKnowledge()
        else:
            ontology_knowledge = ontology_parser.extract_knowledge()

        tanks = analyzer.identify_storage_tanks(nodes)

        if not tanks:
            logger.warning("No storage tanks found in the database.")
            return

        analyzer.analyze_connections(tanks, relationships)

        full_description = analyzer.generate_descriptions(tanks, ontology_knowledge, neo4j_conn)

        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            f.write(full_description)

        print(f"\nAnalysis Complete! Description saved to {OUTPUT_PATH}")
        print("\n--- BEGIN GENERATED DESCRIPTION ---")
        print(full_description)
        print("--- END GENERATED DESCRIPTION ---")

    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)

    finally:
        neo4j_conn.close()

if __name__ == "__main__":
    main()