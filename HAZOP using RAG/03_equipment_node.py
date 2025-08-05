# 03_automatic_noding.py - UPDATED VERSION
# This script creates a distinct HAZOP node for each individual piece of equipment in the graph.

import config
from neo4j import GraphDatabase
import uuid

class AutomaticNoder:
    """
    Connects to the Neo4j database and performs automatic HAZOP noding.
    This version implements a "one node per equipment" strategy.
    """
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

    def create_indexes(self):
        """
        Create indexes to improve query performance.
        """
        print("Creating indexes for better performance...")
        with self.driver.session() as session:
            try:
                session.run("CREATE INDEX hazop_node_id IF NOT EXISTS FOR (n:HAZOPNode) ON (n.nodeID)")
                session.run("CREATE INDEX equipment_id IF NOT EXISTS FOR (e:Equipment) ON (e.Id)")
                session.run("CREATE INDEX equipment_name IF NOT EXISTS FOR (e:Equipment) ON (e.name)")
                print("Indexes created successfully.")
            except Exception as e:
                print(f"Index creation info: {e}")

    def clear_existing_hazop_nodes(self):
        """
        Removes all existing HAZOP nodes to ensure a fresh start.
        """
        print("Clearing any pre-existing HAZOP nodes...")
        with self.driver.session() as session:
            session.run("MATCH (n:HAZOPNode) DETACH DELETE n")
        print("Cleared all pre-existing HAZOP nodes.")

    def create_node_per_equipment(self):
        """
        Main noding logic: Creates one HAZOP node for each :Equipment node,
        naming the HAZOP node based on the equipment's Id.
        """
        print("\nStarting HAZOP noding: one node per equipment...")
        
        self.create_indexes()
        self.clear_existing_hazop_nodes()
        
        nodes_created = 0
        
        with self.driver.session() as session:
            # Get all Equipment nodes from the graph
            equipment_list = list(session.run("MATCH (e:Equipment) RETURN e"))
            print(f"Found {len(equipment_list)} equipment items to process.")
            
            # Iterate through each piece of equipment
            for record in equipment_list:
                equipment_node = record["e"]
                equipment_element_id = equipment_node.element_id
                
                # Get the business Id from the equipment node (e.g., "P-101")
                equipment_id = equipment_node.get('id')

                # Skip any equipment that is missing the 'Id' property
                if not equipment_id:
                    print(f"  - SKIPPING: An equipment node is missing its 'Id' property.")
                    continue

                # --- NEW LOGIC: Create a predictable nodeID based on the Equipment's Id ---
                node_id = f"Node-{equipment_id}"
                description = f"HAZOP analysis for Equipment: {equipment_id}"
                
                # This query remains the same, but uses the new predictable node_id
                session.run("""
                    MATCH (e) WHERE elementId(e) = $element_id
                    CREATE (n:HAZOPNode {nodeID: $node_id, description: $description})
                    MERGE (n)-[:ANALYZES]->(e)
                """, element_id=equipment_element_id, node_id=node_id, description=description)
                
                nodes_created += 1
                print(f"  - Created HAZOPNode '{node_id}' for Equipment '{equipment_id}'")

        print(f"\nAutomatic HAZOP noding complete. Created {nodes_created} nodes.")
        return nodes_created

    def verify_noding_results(self):
        """
        Verify that all Equipment nodes are properly assigned to HAZOP nodes.
        """
        with self.driver.session() as session:
            # Count total equipment components
            total_equipment = session.run("MATCH (e:Equipment) RETURN count(e) AS total").single()["total"]
            
            # --- FIX: Use COUNT(DISTINCT e) to get an accurate count of unique nodes ---
            # This prevents errors if relationships are ever duplicated.
            assigned_equipment = session.run("""
                MATCH (e:Equipment)<-[:ANALYZES]-(:HAZOPNode) 
                RETURN count(DISTINCT e) AS assigned
            """).single()["assigned"]
            
            # Count HAZOP nodes
            hazop_nodes = session.run("MATCH (n:HAZOPNode) RETURN count(n) AS nodes").single()["nodes"]
            
            print("\n--- Noding Verification Results ---")
            print(f"Total Equipment items: {total_equipment}")
            print(f"Assigned Equipment items: {assigned_equipment}")
            print(f"HAZOP nodes created: {hazop_nodes}")
            
            if total_equipment > 0:
                coverage = (assigned_equipment / total_equipment) * 100
                print(f"Coverage: {coverage:.1f}%")
            else:
                print("Coverage: N/A (No equipment found)")

            # Show unassigned equipment if any
            if assigned_equipment < total_equipment:
                unassigned = session.run("""
                    MATCH (e:Equipment)
                    WHERE NOT EXISTS((e)<-[:ANALYZES]-(:HAZOPNode))
                    RETURN e.Id AS id, e.name AS name
                    LIMIT 5
                """)
                print("\nUnassigned Equipment (showing first 5):")
                for record in unassigned:
                    print(f"  - {record['id'] or record['name']}")
        print("---------------------------------")


def main():
    """
    Main function to execute the automatic noding process.
    """
    noder = AutomaticNoder(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)

    try:
        # Perform noding using the "one node per equipment" method
        nodes_created = noder.create_node_per_equipment()
        
        # Verify the results
        noder.verify_noding_results()
        
        if nodes_created == 0:
            print("\nWARNING: No HAZOP nodes were created.")
            print("This might be because no nodes with the label ':Equipment' were found in the graph.")
            
    except Exception as e:
        print(f"An error occurred during the noding process: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close the database connection
        noder.close()

    print("\nPhase 3: Automatic Noding complete.")

if __name__ == "__main__":
    main()