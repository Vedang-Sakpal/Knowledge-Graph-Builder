# This script is UPDATED to automatically treat the entire P&ID graph as a single node.

import config
from neo4j import GraphDatabase

class AutoNoder:
    def __init__(self, uri, user, password):
        """
        Initializes the database driver.
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """
        Closes the database driver connection.
        """
        self.driver.close()

    def create_single_hazop_node(self):
        """
        Creates a single HAZOPNode to represent the entire P&ID graph.
        For larger processes with multiple graphs, run this script for each graph database.
        """
        print("\nCreating a single HAZOPNode for the entire graph...")
        with self.driver.session() as session:
            # 1. Clear any pre-existing HAZOP nodes to ensure a clean slate.
            session.run("MATCH (n:HAZOPNode) DETACH DELETE n")
            print("Cleared any pre-existing HAZOP nodes.")

            # 2. Create a single, system-level HAZOPNode.
            # This node represents the entire P&ID or graph section.
            query = """
            MERGE (n:HAZOPNode {
                nodeID: 'SystemNode',
                description: 'A single node representing the entire P&ID for high-level HAZOP analysis.'
            })
            """
            session.run(query)
            print("Successfully created a single HAZOPNode ('SystemNode') for the graph.")

def main():
    """
    Main function to execute the automatic noding process.
    """
    # Initialize the connection using credentials from the config file
    noder = AutoNoder(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
    
    # Create the single HAZOP node for the entire graph
    noder.create_single_hazop_node()
    
    # Close the database connection
    noder.close()
    
    print("\nPhase 3: Automatic Noding complete.")
    print("The entire graph is now represented by a single HAZOPNode.")

if __name__ == "__main__":
    main()