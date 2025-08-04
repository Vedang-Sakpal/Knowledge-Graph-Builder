# This new script loads the formal HAZOP ontology from the RDF file.
# It parses the ontology to understand the schema (classes and properties)
# and then applies this schema to the Neo4j database by creating constraints.
# This ensures the graph structure adheres to the formal ontology.

# Import the custom configuration file which holds secrets and paths.
import config
# Import the official Neo4j driver to connect to the database.
from neo4j import GraphDatabase
# Import rdflib, a library for working with RDF data (the format for ontologies).
from rdflib import Graph, URIRef, RDFS, OWL
from rdflib.namespace import RDF

class OntologyLoader:
    """
    Loads an OWL/RDF ontology and applies its schema as constraints to Neo4j.
    This class handles connecting to Neo4j, parsing the ontology file,
    and enforcing the ontology's class structure as schema constraints in the graph.
    """
    def __init__(self, rdf_file_path, uri, user, password):
        """
        Initializes the OntologyLoader with database credentials and the ontology file path.
        :param rdf_file_path: Path to the .rdf or .owl ontology file.
        :param uri: The URI for the Neo4j database (e.g., "neo4j://localhost:7687").
        :param user: The username for the Neo4j database.
        :param password: The password for the Neo4j database.
        """
        self.rdf_file = rdf_file_path
        # Create a Neo4j driver instance to manage the database connection.
        self.neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
        # Create an empty rdflib Graph object to hold the parsed ontology.
        self.ontology_graph = Graph()

    def close(self):
        """Closes the connection to the Neo4j database."""
        self.neo4j_driver.close()

    def load_ontology_from_file(self):
        """
        Parses the RDF/XML ontology file into an rdflib graph object in memory.
        """
        try:
            print(f"Loading ontology from {self.rdf_file}...")
            # Use rdflib's parse function to load the file. 'xml' format is common for .owl files.
            self.ontology_graph.parse(self.rdf_file, format="xml")
            # Print a success message with the number of triples (statements) loaded.
            print(f"Successfully loaded ontology with {len(self.ontology_graph)} triples.")
            return True
        except Exception as e:
            # If parsing fails, print an error message and return False.
            print(f"Error parsing ontology file: {e}")
            return False

    def get_classes_from_ontology(self):
        """
        Extracts all defined classes from the parsed ontology graph using a SPARQL query.
        SPARQL is a query language for RDF data, similar to SQL for relational DBs.
        """
        print("Extracting classes from ontology...")
        # SPARQL query to find all subjects that are of type owl:Class.
        # 'a' is shorthand for rdf:type.
        # FILTER ensures we only get resources with a URI, not blank nodes.
        query = """
        SELECT ?class
        WHERE {
            ?class a owl:Class .
            FILTER (isIRI(?class))
        }
        """
        # Execute the query against the in-memory ontology graph.
        results = self.ontology_graph.query(query)
        # The result is a list of URIs. We extract the "fragment" part of the URI
        # (the text after the '#') to get the clean class name.
        classes = [uri.fragment for uri, in results]
        print(f"Found classes: {classes}")
        return classes

    def apply_neo4j_constraints(self, classes):
        """
        Applies uniqueness constraints to the Neo4j database based on the ontology classes.
        This effectively enforces a schema on the graph, improving data integrity and performance.
        """
        print("Applying ontology schema as constraints to Neo4j...")
        # Use a session to execute transactions against the database.
        with self.neo4j_driver.session() as session:
            # --- Step 1: Drop all existing constraints for a clean slate ---
            # This prevents errors from re-running the script or from conflicting old constraints.
            existing_constraints = session.run("SHOW CONSTRAINTS").data()
            for constraint in existing_constraints:
                session.run(f"DROP CONSTRAINT `{constraint['name']}`")
            print("Dropped all existing Neo4j constraints.")

            # --- Step 2: Define the mapping from ontology class to a unique property ---
            # This dictionary is the key part that translates the ontology schema
            # into a practical Neo4j graph schema.
            uniqueness_map = {
                "Cause": "description",
                "Consequence": "description",
                "Safeguard": "description",
                "Deviation": "deviationID",
                "Chemical": "name",
                "Node": "nodeID", # 'Node' in the ontology corresponds to our 'HAZOPNode' in the graph.
                # For all P&ID components, 'name' is the unique identifier.
                "Device": "name",
                "Pipe": "name",
                "Controlling Instrument": "name",
                "Measuring Instrument": "name",
            }
            
            # --- Step 3: Loop through extracted classes and create new constraints ---
            for class_name in classes:
                # Handle the special case where the ontology class 'Node' is named 'HAZOPNode' in our graph.
                label = "HAZOPNode" if class_name == "Node" else class_name
                
                # Check if we have defined a uniqueness rule for this class in our map.
                if label in uniqueness_map:
                    property_key = uniqueness_map[label]
                    # Create a descriptive name for the constraint.
                    constraint_name = f"constraint_unique_{label}_{property_key}"
                    # Construct the Cypher query to create the constraint.
                    # "IF NOT EXISTS" prevents errors if it somehow already exists.
                    # "FOR (n:Label) REQUIRE n.property IS UNIQUE" is the constraint definition.
                    query = f"CREATE CONSTRAINT `{constraint_name}` IF NOT EXISTS FOR (n:{label}) REQUIRE n.{property_key} IS UNIQUE"
                    try:
                        session.run(query)
                        print(f"Applied uniqueness constraint on :{label}({property_key})")
                    except Exception as e:
                        # Catch and print any errors during constraint creation.
                        print(f"Could not apply constraint for {label}: {e}")

def main():
    """Main execution function for Phase 1: Ontology Loading and Schema Enforcement."""
    # Create an instance of the loader, passing in configuration details.
    loader = OntologyLoader(
        config.ONTOLOGY_FILE_PATH,
        config.NEO4J_URI,
        config.NEO4J_USERNAME,
        config.NEO4J_PASSWORD
    )
    # First, attempt to load the ontology file.
    if loader.load_ontology_from_file():
        # If loading is successful, proceed to get the classes...
        classes = loader.get_classes_from_ontology()
        # ...and apply the constraints to the Neo4j database.
        loader.apply_neo4j_constraints(classes)
    
    # Cleanly close the database connection.
    loader.close()
    print("Phase 1: Ontology Loading and Schema Enforcement complete.")

# This standard Python entry point ensures that main() is called only when
# the script is executed directly.
if __name__ == "__main__":
    main()