# This script is UPDATED with the corrected Cypher syntax.

import config
from neo4j import GraphDatabase

class ManualNoder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_all_components(self):
        """Fetches all potential components for HAZOP analysis from the graph."""
        print("Fetching all components from the graph...")
        with self.driver.session() as session:
            # CORRECTED QUERY: Replaced deprecated 'exists(n.name)' with 'n.name IS NOT NULL'
            query = "MATCH (n) WHERE n.name IS NOT NULL RETURN n.name AS name, labels(n)[0] AS type ORDER BY type, name"
            result = session.run(query)
            return [record.data() for record in result]

    def select_nodes(self, components):
        if not components:
            print("No components found in the database.")
            return []
        print("\nPlease select the components to be treated as HAZOP Nodes:")
        for i, comp in enumerate(components):
            print(f"  [{i+1}] {comp['name']} (Type: {comp['type']})")
        while True:
            try:
                selection_str = input("\nEnter the numbers of the nodes to analyze, separated by commas: ")
                selected_indices = [int(s.strip()) - 1 for s in selection_str.split(',')]
                selected_components = [components[i] for i in selected_indices if 0 <= i < len(components)]
                if selected_components:
                    print("\nYou have selected:")
                    for comp in selected_components:
                        print(f"  - {comp['name']}")
                    if input("Is this correct? (yes/no): ").lower() == 'yes':
                        return selected_components
                else:
                    print("No valid nodes selected.")
            except ValueError:
                print("Invalid input.")

    def create_hazop_nodes(self, selected_components):
        print("\nCreating HAZOPNode entities in the graph...")
        with self.driver.session() as session:
            session.run("MATCH (n:HAZOPNode) DETACH DELETE n")
            print("Cleared any pre-existing HAZOP nodes.")
            for comp in selected_components:
                comp_name = comp['name']
                query = """
                MATCH (c {name: $comp_name})
                MERGE (n:HAZOPNode {nodeID: 'Node-' + $comp_name, description: 'Node for ' + labels(c)[0] + ' ' + $comp_name})
                MERGE (n)-[:ANALYZES]->(c)
                """
                session.run(query, comp_name=comp_name)
            print(f"Successfully created {len(selected_components)} HAZOPNode entities.")

def main():
    noder = ManualNoder(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
    all_components = noder.get_all_components()
    selected = noder.select_nodes(all_components)
    if selected:
        noder.create_hazop_nodes(selected)
    else:
        print("No nodes were selected. Halting pipeline.")
        exit()
    noder.close()
    print("Phase 3: Manual Noding complete.")

if __name__ == "__main__":
    main()