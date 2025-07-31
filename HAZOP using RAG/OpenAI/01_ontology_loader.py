# This new script loads the formal HAZOP ontology from the RDF file.
# It parses the ontology to understand the schema (classes and properties)
# and then applies this schema to the Neo4j database by creating constraints.
# This ensures the graph structure adheres to the formal ontology.

import config
from neo4j import GraphDatabase
from rdflib import Graph, URIRef, RDFS, OWL
from rdflib.namespace import RDF

class OntologyLoader:
    """
    Loads an OWL/RDF ontology and applies its schema as constraints to Neo4j.
    """
    def __init__(self, rdf_file_path, uri, user, password):
        self.rdf_file = rdf_file_path
        self.neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
        self.ontology_graph = Graph()

    def close(self):
        self.neo4j_driver.close()

    def load_ontology_from_file(self):
        """Parses the RDF/XML ontology file into an rdflib graph."""
        try:
            print(f"Loading ontology from {self.rdf_file}...")
            self.ontology_graph.parse(self.rdf_file, format="xml")
            print(f"Successfully loaded ontology with {len(self.ontology_graph)} triples.")
            return True
        except Exception as e:
            print(f"Error parsing ontology file: {e}")
            return False

    def get_classes_from_ontology(self):
        """Extracts all defined classes from the parsed ontology graph using SPARQL."""
        print("Extracting classes from ontology...")
        # SPARQL query to find all subjects that are of type owl:Class
        query = """
        SELECT ?class
        WHERE {
            ?class a owl:Class .
            FILTER (isIRI(?class))
        }
        """
        results = self.ontology_graph.query(query)
        # Extract the last part of the URI as the class name
        classes = [uri.fragment for uri, in results]
        print(f"Found classes: {classes}")
        return classes

    def apply_neo4j_constraints(self, classes):
        """
        Applies uniqueness constraints to the Neo4j database based on the ontology classes.
        This enforces the schema.
        """
        print("Applying ontology schema as constraints to Neo4j...")
        with self.neo4j_driver.session() as session:
            # First, drop all existing constraints for a clean slate
            existing_constraints = session.run("SHOW CONSTRAINTS").data()
            for constraint in existing_constraints:
                session.run(f"DROP CONSTRAINT `{constraint['name']}`")
            print("Dropped all existing Neo4j constraints.")

            # Define which property should be unique for each class label.
            # This is a key step in mapping ontology to a graph DB schema.
            uniqueness_map = {
                "Cause": "description",
                "Consequence": "description",
                "Safeguard": "description",
                "Deviation": "deviationID",
                "Chemical": "name",
                "Node": "nodeID", # This corresponds to our HAZOPNode
                # For P&ID components, 'name' is the unique identifier
                "Device": "name",
                "Pipe": "name",
                "Controlling Instrument": "name",
                "Measuring Instrument": "name",
            }
            
            for class_name in classes:
                # The ontology uses 'Node' for the HAZOP study node. We map it to 'HAZOPNode' in our code.
                label = "HAZOPNode" if class_name == "Node" else class_name
                
                if label in uniqueness_map:
                    property_key = uniqueness_map[label]
                    constraint_name = f"constraint_unique_{label}_{property_key}"
                    query = f"CREATE CONSTRAINT `{constraint_name}` IF NOT EXISTS FOR (n:{label}) REQUIRE n.{property_key} IS UNIQUE"
                    try:
                        session.run(query)
                        print(f"Applied uniqueness constraint on :{label}({property_key})")
                    except Exception as e:
                        print(f"Could not apply constraint for {label}: {e}")

def main():
    """Main execution function for Phase 1: Ontology Loading."""
    loader = OntologyLoader(
        config.ONTOLOGY_FILE_PATH,
        config.NEO4J_URI,
        config.NEO4J_USERNAME,
        config.NEO4J_PASSWORD
    )
    if loader.load_ontology_from_file():
        classes = loader.get_classes_from_ontology()
        loader.apply_neo4j_constraints(classes)
    
    loader.close()
    print("Phase 1: Ontology Loading and Schema Enforcement complete.")

if __name__ == "__main__":
    main()
