# 03_automatic_noding.py - UPDATED VERSION
# This script creates a distinct HAZOP node for each individual piece of equipment in the graph.

import config
from neo4j import GraphDatabase

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
        with self.driver.session(database=getattr(config, 'NEO4J_DATABASE', None)) as session:
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
        with self.driver.session(database=getattr(config, 'NEO4J_DATABASE', None)) as session:
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
        
        with self.driver.session(database=getattr(config, 'NEO4J_DATABASE', None)) as session:
            # Get all Equipment nodes from the graph
            equipment_list = list(session.run("MATCH (e:Equipment) RETURN e"))
            print(f"Found {len(equipment_list)} equipment items to process.")
            
            # Iterate through each piece of equipment
            for record in equipment_list:
                equipment_node = record["e"]
                #equipment_element_id = equipment_node.element_id
                equipment_id = equipment_node.get('Id') or equipment_node.get('id') or equipment_node.get('name')

                # Skip any equipment that is missing identifying properties
                if not equipment_id:
                    print("  - SKIPPING: An equipment node is missing its identifying properties ('Id'/'id'/'name').")
                    continue

                # Create a predictable nodeID based on the Equipment's identifier
                node_id = f"Node-{equipment_id}"
                description = f"HAZOP analysis for Equipment: {equipment_id}"
                
                # Link precisely using elementId to avoid accidental matches
                session.run("""
                    MATCH (e) WHERE e.name = $name
                    CREATE (n:HAZOPNode {nodeID: $node_id, description: $description})
                    MERGE (n)-[:ANALYZES]->(e)
                """, name=equipment_id, node_id=node_id, description=description)
                
                nodes_created += 1
                print(f"  - Created HAZOPNode '{node_id}' for Equipment '{equipment_id}'")

        print(f"\nAutomatic HAZOP noding complete. Created {nodes_created} nodes.")
        return nodes_created

    def verify_noding_results(self):
        """
        Verify that all Equipment nodes are properly assigned to HAZOP nodes.
        """
        with self.driver.session(database=getattr(config, 'NEO4J_DATABASE', None)) as session:
            # Debug: Print active database name to ensure we are querying the intended DB
            try:
                dbinfo = session.run("CALL db.info() YIELD name RETURN name").single()
                print(f"\n[Debug] Verifying against database: {dbinfo['name'] if dbinfo else 'unknown'}")
            except Exception:
                pass
            # Count total equipment components
            total_record = session.run("MATCH (e:Equipment) RETURN count(e) AS total").single()
            total_equipment = total_record["total"] if total_record and "total" in total_record else 0
            
            # --- FIX: Use COUNT(DISTINCT e) to get an accurate count of unique nodes ---
            # This prevents errors if relationships are ever duplicated.
            assigned_record = session.run("""
                MATCH (e:Equipment)<-[:ANALYZES]-(:HAZOPNode) 
                RETURN count(DISTINCT e) AS assigned
            """).single()
            assigned_equipment = assigned_record["assigned"] if assigned_record and "assigned" in assigned_record else 0
            
            # Count HAZOP nodes
            hazop_record = session.run("MATCH (n:HAZOPNode) RETURN count(n) AS nodes").single()
            hazop_nodes = hazop_record["nodes"] if hazop_record and "nodes" in hazop_record else 0
            
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
                    WHERE NOT EXISTS { (e)<-[:ANALYZES]-(:HAZOPNode) }
                    RETURN e.name AS name
                    LIMIT 5
                """)
                print("\nUnassigned Equipment (showing first 5):")
                for record in unassigned:
                    print(f"  - {record['name']}")
            elif total_equipment == 0:
                # If zero, show a few nodes with 'name' property to help debug label mismatch
                sample = session.run("MATCH (n) WHERE n.name IS NOT NULL RETURN labels(n) AS labels, n.name AS name LIMIT 5")
                rows = list(sample)
                if rows:
                    print("\n[Debug] Sample nodes with 'name' property (label, name):")
                    for r in rows:
                        print(f"  - {r['labels']}: {r['name']}")
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