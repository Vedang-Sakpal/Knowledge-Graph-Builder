from neo4j import GraphDatabase
import config 

def main():
    """
    Main function to connect to Neo4j, run the Cypher script,
    and list the chemicals.
    """
    try:
        # Establish a connection to the database
        driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD))
        
        # This function executes the main cypher script to create the graph
        def create_graph(tx):
            with open(config.PID_PATH, "r") as cypher_file:
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
            print("Running the Cypher script to create the graph...")
            session.execute_write(create_graph)
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

'''
---------------- Causes ------------------------
Given the deviation for the particular equipment analyze the causes strictly according to the rules given below:
1. Given the Instruments, control loops, and alarms present for the equipment think of causes for that deviation due to failure of any of these elements.
2. Given the operating conditions and the design parameters of the equipment, and also the Chemicals/substances involved, look for damage to the equipment, blockage or leakage due to cause of any of these elements. Also include the causes due to chemical/substances present looking into their safety data and their normal operating conditions and suitable materials of the equipment.
3. Think accordingly if in any equipment have more than one stream is present like separators, heat exchangers, etc. such that the interaction between these streams could lead to deviations. Or any deviation specific to these types of equipment
4. Consider human factors, such as operator actions or maintenance activities, that could contribute to the deviation.
note: Do not assume any equipment or instrument on your own if it doesnt exist in the P&ID. 

--------------- Consequences ------------------------

Given a Cause for the praticular deviation of  node analyze the consequences according to the rules given below :
1. Conisder the consequences due to the chemicals present in the equipment, properties of the chemicals are provided to you. 
2. Consider any adverse effect on the equipment due to the deviation and its causes. 
3. Consider the consequences of damage to humans, environment or human health due to anything as in chemicals, equipment damage, or any issue that is considerable.
4. 
'''