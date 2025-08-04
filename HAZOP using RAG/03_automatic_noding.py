# 03_automatic_noding.py - OPTIMIZED VERSION
# This script automatically identifies and creates HAZOP nodes for distinct process sections.

import config
from neo4j import GraphDatabase
import uuid

class AutomaticNoder:
    """
    Connects to the Neo4j database and performs automatic HAZOP noding.
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
        Create indexes to improve query performance
        """
        print("Creating indexes for better performance...")
        with self.driver.session() as session:
            try:
                # Create index on nodeID for HAZOPNode
                session.run("CREATE INDEX hazop_node_id IF NOT EXISTS FOR (n:HAZOPNode) ON (n.nodeID)")
                # Create indexes on equipment properties
                session.run("CREATE INDEX equipment_id IF NOT EXISTS FOR (e:Equipment) ON (e.id)")
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

    def get_all_components(self):
        """
        Get all components in the graph that should be analyzed
        """
        with self.driver.session() as session:
            query = """
            MATCH (c)
            WHERE c:Equipment OR c:Utility_and_supply OR c:Piping_and_fitting OR c:Miscellaneous
            AND NOT EXISTS((c)<-[:ANALYZES]-(:HAZOPNode))
            RETURN c
            """
            result = session.run(query)
            return [record["c"] for record in result]

    def find_connected_components(self, start_node_id):
        """
        Find all components connected to the start node within reasonable depth
        """
        with self.driver.session() as session:
            query = """
            MATCH (start {id: $start_id})
            WHERE NOT EXISTS((start)<-[:ANALYZES]-(:HAZOPNode))
            CALL {
                WITH start
                MATCH path = (start)-[:Connected_to*1..5]-(connected)
                WHERE (connected:Equipment OR connected:Utility_and_supply 
                       OR connected:Piping_and_fitting OR connected:Miscellaneous)
                AND NOT EXISTS((connected)<-[:ANALYZES]-(:HAZOPNode))
                RETURN collect(DISTINCT connected) + [start] AS section
            }
            RETURN section[0] AS components
            """
            result = session.run(query, start_id=start_node_id)
            record = result.single()
            return record["components"] if record else []

    def create_hazop_node_for_section(self, components):
        """
        Create a HAZOP node for a section of components
        """
        if not components:
            return None
            
        with self.driver.session() as session:
            # Generate a simple UUID using Python's uuid module
            node_id = f"Node-{str(uuid.uuid4())[:8]}"
            
            # Create the HAZOP node
            session.run("""
                CREATE (n:HAZOPNode {
                    nodeID: $node_id, 
                    description: $description
                })
            """, node_id=node_id, 
                description=f'Automated node for process section containing {len(components)} components')
            
            # Link all components to this HAZOP node
            for component in components:
                component_id = component.get('id') or component.get('name', 'unknown')
                session.run("""
                    MATCH (n:HAZOPNode {nodeID: $node_id})
                    MATCH (c) WHERE (c.id = $comp_id OR c.name = $comp_id)
                    MERGE (n)-[:ANALYZES]->(c)
                """, node_id=node_id, comp_id=component_id)
            
            return node_id

    def automatic_noding_optimized(self):
        """
        Optimized automatic HAZOP noding that processes components efficiently
        """
        print("\nStarting optimized automatic HAZOP noding...")
        
        # Create indexes first
        self.create_indexes()
        
        # Clear existing HAZOP nodes
        self.clear_existing_hazop_nodes()
        
        nodes_created = 0
        processed_components = set()
        
        with self.driver.session() as session:
            # Get all components that need to be assigned to HAZOP nodes
            all_components = self.get_all_components()
            print(f"Found {len(all_components)} components to process")
            
            for component in all_components:
                comp_id = component.get('id') or component.get('name', 'unknown')
                
                # Skip if already processed
                if comp_id in processed_components:
                    continue
                
                # Find all connected components using limited depth search
                query = """
                MATCH (start) 
                WHERE (start.id = $comp_id OR start.name = $comp_id)
                AND NOT EXISTS((start)<-[:ANALYZES]-(:HAZOPNode))
                
                CALL {
                    WITH start
                    MATCH path = (start)-[:Connected_to*0..3]-(connected)
                    WHERE (connected:Equipment OR connected:Utility_and_supply 
                           OR connected:Piping_and_fitting OR connected:Miscellaneous)
                    AND NOT EXISTS((connected)<-[:ANALYZES]-(:HAZOPNode))
                    RETURN collect(DISTINCT connected) AS section
                }
                
                RETURN section
                """
                
                result = session.run(query, comp_id=comp_id)
                record = result.single()
                
                if record and record["section"]:
                    section_components = record["section"]
                    
                    # Create HAZOP node for this section
                    node_id = f"Node-{str(uuid.uuid4())[:8]}"
                    
                    # Get component names/ids for description
                    comp_names = []
                    for comp in section_components:
                        name = comp.get('id') or comp.get('name', 'unknown')
                        comp_names.append(name)
                        processed_components.add(name)
                    
                    description = f"Process section: {', '.join(comp_names[:3])}"
                    if len(comp_names) > 3:
                        description += f" + {len(comp_names)-3} more"
                    
                    # Create the HAZOP node
                    session.run("""
                        CREATE (n:HAZOPNode {
                            nodeID: $node_id, 
                            description: $description
                        })
                    """, node_id=node_id, description=description)
                    
                    # Link components to HAZOP node
                    for comp in section_components:
                        comp_identifier = comp.get('id') or comp.get('name')
                        if comp_identifier:
                            session.run("""
                                MATCH (n:HAZOPNode {nodeID: $node_id})
                                MATCH (c) WHERE (c.id = $comp_id OR c.name = $comp_id)
                                MERGE (n)-[:ANALYZES]->(c)
                            """, node_id=node_id, comp_id=comp_identifier)
                    
                    nodes_created += 1
                    print(f"Created HAZOPNode {node_id} for {len(section_components)} components")
        
        print(f"\nAutomatic HAZOP noding complete. Created {nodes_created} nodes.")
        return nodes_created

    def verify_noding_results(self):
        """
        Verify that all components are properly assigned to HAZOP nodes
        """
        with self.driver.session() as session:
            # Count total components
            total_components = session.run("""
                MATCH (c)
                WHERE c:Equipment OR c:Utility_and_supply OR c:Piping_and_fitting OR c:Miscellaneous
                RETURN count(c) AS total
            """).single()["total"]
            
            # Count assigned components
            assigned_components = session.run("""
                MATCH (c)<-[:ANALYZES]-(:HAZOPNode)
                WHERE c:Equipment OR c:Utility_and_supply OR c:Piping_and_fitting OR c:Miscellaneous
                RETURN count(c) AS assigned
            """).single()["assigned"]
            
            # Count HAZOP nodes
            hazop_nodes = session.run("""
                MATCH (n:HAZOPNode)
                RETURN count(n) AS nodes
            """).single()["nodes"]
            
            print(f"\nNoding Results:")
            print(f"Total components: {total_components}")
            print(f"Assigned components: {assigned_components}")
            print(f"HAZOP nodes created: {hazop_nodes}")
            print(f"Coverage: {assigned_components/total_components*100:.1f}%" if total_components > 0 else "No components found")
            
            # Show unassigned components if any
            if assigned_components < total_components:
                unassigned = session.run("""
                    MATCH (c)
                    WHERE (c:Equipment OR c:Utility_and_supply OR c:Piping_and_fitting OR c:Miscellaneous)
                    AND NOT EXISTS((c)<-[:ANALYZES]-(:HAZOPNode))
                    RETURN c.id AS id, c.name AS name, labels(c) AS labels
                    LIMIT 5
                """)
                
                print("\nUnassigned components (showing first 5):")
                for record in unassigned:
                    print(f"  - {record['id'] or record['name']} ({record['labels']})")

def main():
    """
    Main function to execute the automatic noding process.
    """
    # Initialize the connection using credentials from the config file
    noder = AutomaticNoder(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)

    try:
        # Perform automatic noding with the optimized method
        nodes_created = noder.automatic_noding_optimized()
        
        # Verify the results
        noder.verify_noding_results()
        
        if nodes_created == 0:
            print("\nWARNING: No HAZOP nodes were created!")
            print("This might be because:")
            print("1. All components are already assigned to HAZOP nodes")
            print("2. No components match the expected labels (Equipment, Utility_and_supply, etc.)")
            print("3. There are no Connected_to relationships in the graph")
            
    except Exception as e:
        print(f"Error during noding process: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close the database connection
        noder.close()

    print("\nPhase 3: Automatic Noding complete.")

if __name__ == "__main__":
    main()