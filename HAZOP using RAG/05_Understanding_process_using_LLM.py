import google.generativeai as genai
import config

def get_llm_process_analysis(cypher_script_content, process_description_content):
    """
    Uses a Generative LLM to analyze and describe a process flow.

    Args:
        cypher_script_content (str): The string content of the Cypher script defining the graph.
        process_description_content (str): The string content of the Markdown process description.

    Returns:
        str: The LLM-generated analysis of the process.
    """
    # --- Prompt Engineering ---
    # This detailed prompt guides the LLM to synthesize the provided documents.
    prompt = f"""
    You are an expert process engineer specializing in analyzing chemical plant P&IDs and documentation.
    Your task is to synthesize the provided P&ID data (as a Cypher script) and a process description 
    (in Markdown) to create a comprehensive analysis of the material and energy/control flow for the 
    Sour Water Stripper plant.

    --- P&ID DATA (CYPHER SCRIPT) ---
    {cypher_script_content}
    --- END OF CYPHER SCRIPT ---

    --- PROCESS DESCRIPTION (MARKDOWN) ---
    {process_description_content}
    --- END OF PROCESS DESCRIPTION ---

    Based on BOTH documents provided above, please perform the following analysis:

    1.  **Identify Main Material Streams**: Trace the primary flow paths from their source, through all major equipment, to their final sink. Describe what is happening at each stage.
    2.  **Describe Key Equipment and Purpose**: For each major piece of equipment (e.g., Surge Drum, Stripper Column), explain its role in the process, referencing both documents.
    3.  **Detail the Control and Energy Flows**: Explain how the process is controlled. Describe the key control loops, mentioning the sensor, the controller, and the final control element (like a valve or pump) it operates. Steam injection represents the primary energy input.
    4.  **Summarize Inputs and Outputs**: List the main chemical inputs to the entire process and all the final products or waste streams leaving the system.

    Format your response using clear Markdown headings for each section.
    """

    print("🤖 Sending consolidated data to the LLM for analysis...")
    model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
    response = model.generate_content(prompt)
    
    return response.text

# --- Example Usage ---
if __name__ == '__main__':
    # Make sure to set your GOOGLE_API_KEY as an environment variable
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
    except KeyError:
        print("🚨 Error: GOOGLE_API_KEY environment variable not set.")
        print("Please set your API key to run this script.")
        exit()

    # Read the source files
    try:
        with open(config.PID_PATH, "r") as f:
            cypher_content = f.read()
        with open(config.PROCESS_DESCRIPTION_PATH, "r") as f:
            md_content = f.read()
    except FileNotFoundError as e:
        print(f"🚨 Error: Could not find a required file: {e.filename}")
        exit()

    # Get the analysis from the LLM
    llm_analysis = get_llm_process_analysis(cypher_content, md_content)

    # Print the result
    print("\n✅ LLM Analysis Complete. Here is the generated report:")
    print("========================= GENERATED LLM ANALYSIS =========================")
    print(llm_analysis)
    with open("Process_Description/Generated_process_description.md", "w", encoding="utf-8") as f:
        f.write(llm_analysis)
    print("\n✅ Analysis has been saved to Generated_process_description.md")
    print("========================================================================")
    
    '''
    Now after excuting this process description creation code i have excuted this equipment code then now i want to write a code that will do the following tasks :

1. ask me that of which HAZOPnode i have to conduct the HAZOP analysis and take my input

2. using the parameter guideword csv file generate all the applicable devtiation for the particular selected node/nodes

3. now using the generated process description and P&ID graph stored in neo4j databse i wnat to provide context to the LLM to further carry a professional level HAZOP analysis and generate causes, consequences and safeguards for the node.

4. while generating the causes 
'''
