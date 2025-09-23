from neo4j import GraphDatabase
import config 
import argparse # Import argparse

def main():
    """
    Main function to connect to Neo4j, run the Cypher script,
    and list the chemicals.
    """
    # --- Add Argument Parser ---
    parser = argparse.ArgumentParser(description="Parse a P&ID Cypher file and load it into Neo4j.")
    parser.add_argument("--file", required=True, help="Path to the .cypher P&ID file to parse.")
    args = parser.parse_args()
    
    try:
        # Establish a connection to the database
        driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD))
        
        # This function executes the main cypher script to create the graph
        def create_graph(tx, cypher_file_path):
            print(f"Reading Cypher script from: {cypher_file_path}")
            with open(cypher_file_path, "r") as cypher_file:
                cypher_query = cypher_file.read()
            tx.run(cypher_query)

        # This function queries for the chemical names
        def get_chemicals(tx):
            results = tx.run("MATCH (c:Chemical) RETURN c.name AS chemical_name")
            return [record["chemical_name"] for record in results]

        with driver.session() as session:
            # First, clear the database to avoid duplicate data on re-runs (optional)
            print("Clearing the database...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # Execute the Cypher script to create the graph
            print(f"Running the Cypher script '{args.file}' to create the graph...")
            session.execute_write(create_graph, args.file) # Pass the file path
            print("Graph has been successfully created.")

            # Now, query for the chemicals
            print("\nFetching chemical names from the database...")
            chemicals = session.execute_read(get_chemicals)
            
            # Print the list of chemicals
            if chemicals:
                print("\n--- Different Chemicals Mentioned ---")
                for chemical in chemicals:
                    print(f"- {chemical}")
            else:
                print("No chemicals found in the database.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if 'driver' in locals() and driver:
            driver.close()

if __name__ == "__main__":
    main()