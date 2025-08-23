import csv
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from neo4j import GraphDatabase
import google.generativeai as genai
#from openpyxl import Workbook
#from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# Assuming config.py exists with your API keys and Neo4j credentials
import config


def get_driver() -> GraphDatabase.driver:
    """Establishes connection to the Neo4j database."""
    return GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD))


def fetch_equipment_nodes(session) -> List[Dict[str, str]]:
    """Fetches all equipment nodes from the Neo4j database."""
    query = """
    MATCH (e:Equipment)
    RETURN e.name AS name, e.type AS type
    ORDER BY name
    """
    result = session.run(query)
    return [dict(record) for record in result]


def fetch_equipment_context(session, equipment_name: str) -> dict:
    """
    Fetches the context for a specific piece of equipment, including connected
    sensors and valves.
    """
    q = """
    MATCH (e:Equipment {name: $name})
    OPTIONAL MATCH (s:Sensor)-[:CONNECTED_TO]->(e)
    OPTIONAL MATCH (v_in:Valve)-[:FLOWS_TO]->(e)
    OPTIONAL MATCH (e)-[:FLOWS_TO]->(v_out:Valve)
    WITH e, 
         collect(DISTINCT s {name: s.name, type: s.type}) AS sensors, 
         collect(DISTINCT v_in {name: v_in.name, type: v_in.type}) AS incoming_valves,
         collect(DISTINCT v_out {name: v_out.name, type: v_out.type}) AS outgoing_valves
    RETURN {
        equipment: e.name,
        type: e.type,
        sensors: sensors,
        incoming_valves: incoming_valves,
        outgoing_valves: outgoing_valves
    } AS context
    """
    result = session.run(q, name=equipment_name).single()
    return result['context'] if result else {"sensors": [], "valves": []}


def load_applicable_deviations(equipment_name: str) -> List[Dict[str, str]]:
    """Load applicable deviations for the selected equipment from the CSV."""
    deviations = []
    try:
        with open("Applicable_Deviations.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["EquipmentName"] == equipment_name:
                    deviations.append({
                        "parameter": row["Parameter"],
                        "guideword": row["Guideword"],
                        "rationale": row["Rationale"]
                    })
    except FileNotFoundError:
        print("Warning: Applicable_Deviations.csv not found. Will use generic deviations.")
    
    return deviations


def load_process_description() -> str:
    """Load the generated process description."""
    try:
        with open("Generated_process_description.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Process description not available."


def configure_llm():
    """Configures and returns the Generative AI model."""
    genai.configure(api_key=config.GEMINI_API_KEY)
    return genai.GenerativeModel(config.GEMINI_MODEL_NAME)


def save_and_parse_llm_json(llm_raw_text: str, equipment_name: str) -> Optional[List[Dict[str, Any]]]:
    """
    Saves the raw LLM text output to a file, then cleans and parses it into a structured list.
    This prevents parsing errors by isolating the raw output first.
    """
    # Define the filename for the raw output
    raw_filename = f"HAZOP_Analysis_{equipment_name.replace(' ', '_')}_raw_output.json"

    # --- Step 1: Clean the raw text ---
    # Remove markdown code fences (e.g., ```json ... ```) and strip whitespace
    cleaned_text = re.sub(r'```json\s*|```', '', llm_raw_text).strip()

    # --- Step 2: Save the cleaned, raw JSON output to a file ---
    try:
        with open(raw_filename, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
        print(f"   -> LLM raw output saved to: {raw_filename}")
    except IOError as e:
        print(f"Error saving raw LLM output file: {e}")
        return None

    # --- Step 3: Parse the cleaned text into a Python object ---
    try:
        data = json.loads(cleaned_text)
        
        # --- Step 4: Normalize the data structure to ensure consistency ---
        if not isinstance(data, list):
            print("Warning: LLM output was not a list as expected. The output will be wrapped in a list.")
            data = [data]

        normalized = []
        for item in data:
            if not isinstance(item, dict):
                continue  # Skip any non-dictionary items in the list
            normalized.append({
                "parameter": item.get("parameter", "N/A"),
                "guideword": item.get("guideword", "N/A"),
                "causes": item.get("causes") if isinstance(item.get("causes"), list) else [str(item.get("causes", "N/A"))],
                "consequences": item.get("consequences") if isinstance(item.get("consequences"), list) else [str(item.get("consequences", "N/A"))],
                "safeguards": item.get("safeguards") if isinstance(item.get("safeguards"), list) else [str(item.get("safeguards", "N/A"))]
            })
        return normalized
    except json.JSONDecodeError as e:
        print(f"❌ Critical Error: Failed to parse JSON from the LLM's response. {e}")
        print(f"   Please check the raw output file for issues: {raw_filename}")
        return None


def conduct_hazop_analysis(model, equipment: Dict[str, str], context: Dict[str, Any], 
                          deviations: List[Dict[str, str]], process_description: str) -> Optional[List[Dict[str, Any]]]:
    """
    Conducts HAZOP analysis using the LLM and returns the parsed, structured result.
    """

    prompt = {
        "analysis_task": "Perform HAZOP analysis based on the following data.",
        "equipment": {
            "name": equipment.get("name"),
            "type": equipment.get("type"),
        },
        "p&id_context": context,
        "process_description": process_description,
        "deviations_to_analyze": deviations,
        "required_output_format": "[{\"parameter\": \"...\", \"guideword\": \"...\", \"causes\": [\"...\"], \"consequences\": [\"...\"], \"safeguards\": [\"...\"]}, ...]"
    }

    response = model.generate_content(
        [
            {"role": "user", "parts": [json.dumps(prompt, indent=2)]}
        ]
    )
    raw_text = (response.text or "").strip()
    
    # NEW: Use the robust save-and-parse function
    parsed_analysis = save_and_parse_llm_json(raw_text, equipment['name'])
    
    return parsed_analysis
        

def display_equipment_list(equipments: List[Dict[str, str]]):
    """Display numbered list of available equipment."""
    print("\n=== Available Equipment ===")
    for i, eq in enumerate(equipments, 1):
        print(f"{i}. {eq['name']} ({eq['type']})")


def get_equipment_selection(equipments: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Get equipment selection from user."""
    while True:
        try:
            choice = input("\nEnter equipment number (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(equipments):
                return equipments[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(equipments)}")
        except ValueError:
            print("Please enter a valid number")


def save_hazop_report_csv(equipment_name: str, analysis_data: List[Dict[str, Any]]):
    """Save HAZOP analysis to a CSV file from the structured analysis data."""
    filename = f"Results/HAZOP_Analysis_{equipment_name.replace(' ', '_')}.csv"
    
    # Check if analysis_data is valid
    if not analysis_data:
        print("⚠️ No valid analysis data provided. CSV report will not be generated.")
        # Optionally create a CSV with an error message
        with open(filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Error"])
            writer.writerow(["Failed to generate HAZOP analysis due to parsing error. See console for details."])
        return

    # Write CSV
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            "Equipment", "Parameter", "Guideword", "Deviation",
            "Causes", "Consequences", "Safeguards", "Analysis Date"
        ])
        
        # Write rows
        for d in analysis_data:
            parameter = d.get("parameter", "N/A")
            guideword = d.get("guideword", "N/A")
            deviation = f"{parameter} {guideword}".strip()
            
            # Join list items with a semicolon for better CSV readability
            causes = "; ".join(d.get("causes", []))
            consequences = "; ".join(d.get("consequences", []))
            safeguards = "; ".join(d.get("safeguards", []))
            
            writer.writerow([
                equipment_name, parameter, guideword, deviation,
                causes, consequences, safeguards,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ])
    
    print(f"\n✅ HAZOP analysis saved to CSV: {filename}")


def main():
    """Main function to run the HAZOP analysis tool."""
    print("=== Professional HAZOP Analysis Tool ===\n")
    
    model = configure_llm()
    process_description = load_process_description()
    
    driver = get_driver()
    try:
        with driver.session() as session:
            equipments = fetch_equipment_nodes(session)
            if not equipments:
                print("No equipment found in the database.")
                return
            
            while True:
                display_equipment_list(equipments)
                selected_equipment = get_equipment_selection(equipments)
                if selected_equipment is None:
                    break
                
                equipment_name = selected_equipment["name"]
                print(f"\n--- Starting HAZOP for: {equipment_name} ---\n")
                
                print("1. Fetching P&ID context from Neo4j...")
                context = fetch_equipment_context(session, equipment_name)
                
                print("2. Loading applicable deviations from CSV...")
                deviations = load_applicable_deviations(equipment_name)
                if not deviations:
                    print("   -> No specific deviations found. Using a generic deviation for analysis.")
                    deviations = [{"parameter": "Process", "guideword": "General Malfunction", "rationale": "Generic analysis due to lack of specific deviations."}]
                
                print("3. Conducting HAZOP analysis with LLM... (This may take a moment)")
                analysis = conduct_hazop_analysis(model, selected_equipment, context, deviations, process_description)

                # Check if the analysis was successful before saving
                if analysis:
                    print("4. Saving HAZOP report to CSV...")
                    save_hazop_report_csv(equipment_name, analysis)
                else:
                    print("\nSkipping report generation due to an error in the analysis step.")

                another = input("\nAnalyze another piece of equipment? (y/n): ").strip().lower()
                if another != 'y':
                    break
                
    finally:
        driver.close()
    
    print("\nHAZOP analysis complete!")


if __name__ == "__main__":
    main()