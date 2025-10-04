import google.generativeai as genai
import config
from neo4j import GraphDatabase, exceptions # Import the Neo4j driver
import argparse # Import argparse
import os 

def get_graph_data_from_neo4j():
    """
    Connects to the Neo4j database and fetches the entire graph as a
    Cypher script. This requires the APOC library to be installed in Neo4j.

    Returns:
        str: A string containing the Cypher script to recreate the graph.
    """
    uri = config.NEO4J_URI
    user = config.NEO4J_USERNAME
    password = config.NEO4J_PASSWORD
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    cypher_script_from_db = ""
    query = "CALL apoc.export.cypher.all(null, {stream:true, format:'plain', useOptimizations: {type: 'none'}})"

    with driver.session() as session:
        print(" Querying Neo4j database to retrieve P&ID graph data...")
        try:
            result = session.run(query)
            for record in result:
                cypher_script_from_db += record["cypherStatements"]
            print(" Successfully retrieved graph data from Neo4j.")
        except exceptions.ClientError as e:
            if "Unknown procedure" in e.message:
                print(" Error: The APOC procedure 'apoc.export.cypher.all' was not found.")
                print("Please ensure the APOC plugin is correctly installed in your Neo4j database.")
                return None
            else:
                raise e

    driver.close()
    return cypher_script_from_db

def get_llm_process_analysis(cypher_script_content, process_description_content=None):
    """
    Uses a Generative LLM to analyze and describe a process flow.
    It dynamically adjusts the prompt based on whether a process description is provided.
    
    Args:
        cypher_script_content (str): The string content of the Cypher script defining the graph.
        process_description_content (str, optional): The string content of the Markdown 
                                                    process description. Defaults to None.

    Returns:
        str: The LLM-generated analysis of the process.
    """
    # Dynamic Prompt Engineering
    if process_description_content:
        prompt = f"""
        You are an expert process engineer specializing in analyzing chemical plant P&IDs and documentation.
        Your task is to synthesize BOTH the provided P&ID data (as a Cypher script) AND a process description 
        to create a comprehensive analysis of the material and energy/control flow for the given plant.

        --- P&ID DATA (CYPHER SCRIPT FROM NEO4J DATABASE) ---
        {cypher_script_content}
        --- END OF CYPHER SCRIPT ---

        --- PROCESS DESCRIPTION ---
        {process_description_content}
        --- END OF PROCESS DESCRIPTION ---

        Based on BOTH documents provided above, please perform the following analysis:

        1.  **Identify Main Material Streams**: Trace the primary flow paths from their source, through all major equipment, to their final sink. Describe what is happening at each stage. Name the specific chemicals flowing.
        2.  **Describe Key Equipment and Purpose**: For each major piece of equipment, explain its role in the process, referencing both documents.
        3.  **Detail the Control and Energy Flows**: Explain how the process is controlled. Describe the key control loops, mentioning the sensor, the controller, and the final control element (like a valve or pump) it operates.
        4.  **Summarize Inputs and Outputs**: List the main chemical inputs to the entire process and all the final products or waste streams leaving the system.

        Format your response using clear Markdown headings for each section.
        """
    else:
        prompt = f"""
        You are an expert process engineer specializing in analyzing chemical plant P&IDs.
        Your task is to analyze the provided P&ID data (as a Cypher script) to create a comprehensive analysis 
        of the material and energy/control flow for the given chemical plant.

        --- P&ID DATA (CYPHER SCRIPT FROM NEO4J DATABASE) ---
        {cypher_script_content}
        --- END OF CYPHER SCRIPT ---

        Based on the P&ID data provided above, please perform the following analysis:

        1.  **Identify Main Material Streams**: Trace the primary flow paths from their source, through all major equipment, to their final sink. Describe what is happening at each stage. Name the specific chemicals flowing.
        2.  **Describe Key Equipment and Purpose**: For each major piece of equipment, explain its role in the process based on its connections and labels.
        3.  **Detail the Control and Energy Flows**: Explain how the process is controlled. Describe the key control loops, mentioning the sensor, the controller, and the final control element (like a valve or pump) it operates.
        4.  **Summarize Inputs and Outputs**: List the main chemical inputs to the entire process and all the final products or waste streams leaving the system.

        Format your response using clear Markdown headings for each section.
        """

    print("Sending data to the LLM for analysis...")
    model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
    response = model.generate_content(prompt)
    
    return response.text

# --- Main execution block ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a process understanding document using an LLM.")
    parser.add_argument("--description-file", help="Optional path to the process description Text file (.txt).")
    args = parser.parse_args()
    
    # Configure the Generative AI model
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
    except AttributeError:
        print(" Error: GEMINI_API_KEY not found in config.py.")
        print("Please set your API key to run this script.")
        exit()

    try:
        # 1. Get P&ID data by querying the Neo4j database
        cypher_content = get_graph_data_from_neo4j()
        if not cypher_content: # Exit if the database query failed
            print("Could not retrieve data from Neo4j. Aborting analysis.")
            exit()
            
        # 3. Read the optional process description file
        if args.description_file:
            print(f"Reading optional process description from: {args.description_file}")
            try:
                with open(args.description_file, "r") as f:
                    md_content = f.read()
            except FileNotFoundError as e:
                print(f"Error: Could not find the process description file: {e.filename}")
                exit()
    except Exception as e:
        print(f"An unexpected error occurred during data preparation: {e}")
        exit()

    # 4. Get the analysis from the LLM
    llm_analysis = get_llm_process_analysis(cypher_content, md_content)

    # 5. Print and save the LLM result
    print("\nLLM Analysis Complete. Here is the generated report:")
    print("========================= GENERATED LLM ANALYSIS =========================")
    print(llm_analysis)
    
    output_filename = "Results/Generated_process_description.md"
    os.makedirs(os.path.dirname(output_filename), exist_ok=True) # Ensure directory exists
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(llm_analysis)
    print(f"\nAnalysis has been saved to {output_filename}")
    print("========================================================================")