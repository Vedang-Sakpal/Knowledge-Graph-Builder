import google.generativeai as genai
import config
from neo4j import GraphDatabase, exceptions # Import the Neo4j driver

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
    
    # This APOC query exports the entire database into a single Cypher script.
    # The {stream:true} config is added to send the output directly to the
    # client instead of a file, bypassing the server's security setting.
    # --- THIS IS THE MODIFIED LINE ---
    query = "CALL apoc.export.cypher.all(null, {stream:true, format:'plain', useOptimizations: {type: 'none'}})"

    with driver.session() as session:
        print("🔍 Querying Neo4j database to retrieve P&ID graph data...")
        try:
            result = session.run(query)
            # The result is a stream of records; we concatenate them.
            for record in result:
                cypher_script_from_db += record["cypherStatements"]
            print("✅ Successfully retrieved graph data from Neo4j.")
        except exceptions.ClientError as e:
            if "Unknown procedure" in e.message:
                print("🚨 Error: The APOC procedure 'apoc.export.cypher.all' was not found.")
                print("Please ensure the APOC plugin is correctly installed in your Neo4j database.")
                return None
            else:
                raise e

    driver.close()
    return cypher_script_from_db

def get_llm_process_analysis(cypher_script_content, process_description_content):
    """
    Uses a Generative LLM to analyze and describe a process flow.
    (This function remains unchanged from your original script)
    
    Args:
        cypher_script_content (str): The string content of the Cypher script defining the graph.
        process_description_content (str): The string content of the Markdown process description.

    Returns:
        str: The LLM-generated analysis of the process.
    """
    # --- Prompt Engineering ---
    prompt = f"""
    You are an expert process engineer specializing in analyzing chemical plant P&IDs and documentation.
    Your task is to synthesize the provided P&ID data (as a Cypher script) and a process description 
    (in Markdown) to create a comprehensive analysis of the material and energy/control flow for the 
    given chemical plant.

    --- P&ID DATA (CYPHER SCRIPT FROM NEO4J DATABASE) ---
    {cypher_script_content}
    --- END OF CYPHER SCRIPT ---

    --- PROCESS DESCRIPTION (MARKDOWN) ---
    {process_description_content}
    --- END OF PROCESS DESCRIPTION ---

    Based on BOTH documents provided above, please perform the following analysis:

    1.  **Identify Main Material Streams**: Trace the primary flow paths from their source, through all major equipment, to their final sink. Describe what is happening at each stage.
    2.  **Describe Key Equipment and Purpose**: For each major piece of equipment, explain its role in the process, referencing both documents.
    3.  **Detail the Control and Energy Flows**: Explain how the process is controlled. Describe the key control loops, mentioning the sensor, the controller, and the final control element (like a valve or pump) it operates.
    4.  **Summarize Inputs and Outputs**: List the main chemical inputs to the entire process and all the final products or waste streams leaving the system.

    Format your response using clear Markdown headings for each section.
    """

    print("🤖 Sending consolidated data to the LLM for analysis...")
    model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
    response = model.generate_content(prompt)
    
    return response.text

# --- Main execution block ---
if __name__ == '__main__':
    # Configure the Generative AI model
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
    except AttributeError:
        print("🚨 Error: GEMINI_API_KEY not found in config.py.")
        print("Please set your API key to run this script.")
        exit()

    try:
        # 1. Get P&ID data by querying the Neo4j database
        cypher_content = get_graph_data_from_neo4j()
        if not cypher_content: # Exit if the database query failed
            print("Could not retrieve data from Neo4j. Aborting analysis.")
            exit()
            
        # 2. Read the process description file
        with open(config.PROCESS_DESCRIPTION_PATH, "r") as f:
            md_content = f.read()

    except FileNotFoundError as e:
        print(f"🚨 Error: Could not find the process description file: {e.filename}")
        exit()
    except exceptions.AuthError:
        print("🚨 Error: Neo4j authentication failed. Please check your credentials in config.py.")
        exit()
    except Exception as e:
        print(f"🚨 An unexpected error occurred: {e}")
        exit()

    # Get the analysis from the LLM
    llm_analysis = get_llm_process_analysis(cypher_content, md_content)

    # Print and save the result
    print("\n✅ LLM Analysis Complete. Here is the generated report:")
    print("========================= GENERATED LLM ANALYSIS =========================")
    print(llm_analysis)
    
    output_filename = "Results/Generated_process_description.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(llm_analysis)
    print(f"\n✅ Analysis has been saved to {output_filename}")
    print("========================================================================")