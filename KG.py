import csv
from collections import defaultdict
from typing import List, Dict
import openai  # Make sure you have openai installed and your API key set
import os  # <-- Add this line to use environment variables
from dotenv import load_dotenv  # <-- Add this line to load .env file

load_dotenv()  # <-- Load environment variables from .env

# Helper function to call LLM for relationship extraction (if needed)
def extract_relationships_llm(row: Dict[str, str], system_prompt: str, api_key: str) -> Dict[str, List[str]]:
    openai.api_key = api_key
    user_prompt = f"Given the following HAZOP row:\n{row}\nExtract the relationships as a Python dictionary with keys: 'causes', 'consequences', 'safeguards', 'actions'."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=256,
        temperature=0
    )
    try:
        relationships = eval(response.choices[0].message['content'])
        return relationships
    except Exception:
        return {
            "causes": [],
            "consequences": [],
            "safeguards": [],
            "actions": []
        }

def generate_cypher_from_hazop_csv(csv_path, output_file=None, use_llm=False, openai_api_key=None):
    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    cypher_queries = []
    process_name = "Chemical Batch Process"

    for row in rows:
        parameter = row.get('Parameter', '').strip()
        deviation = row.get('Deviation', '').strip()
        cause = row.get('Possible Cause', '').strip()
        consequence = row.get('Consequence', '').strip()
        safeguard = row.get('Safeguard/Protection', '').strip()
        action = row.get('Action', '').strip()
        assigned = row.get('On', '').strip()
        ref = row.get('Ref.', '').strip() or row.get('No', '').strip()

        # Use LLM to extract relationships if requested
        if use_llm and openai_api_key:
            system_prompt = (
                "You are an expert in process safety and knowledge graph construction. "
                "Given a HAZOP row, extract the causes, consequences, safeguards, and actions as lists."
            )
            relationships = extract_relationships_llm(row, system_prompt, openai_api_key)
            causes = relationships.get("causes", [])
            consequences = relationships.get("consequences", [])
            safeguards = relationships.get("safeguards", [])
            actions = relationships.get("actions", [])
        else:
            causes = [cause] if cause else []
            consequences = [consequence] if consequence else []
            safeguards = [s.strip() for s in safeguard.split('.') if s.strip()]
            actions = [{"description": action, "assigned": assigned, "ref": ref}] if action else []

        # Only process if deviation and parameter exist
        if deviation and parameter:
            query = f"""
// Processing Ref {ref} - {parameter}/{deviation}
MERGE (p:Process {{name: "{process_name}"}});
MERGE (param:Parameter {{name: "{parameter}"}});
MERGE (p)-[:HAS_PARAMETER]->(param);

MERGE (dev:Deviation {{name: "{deviation}", ref: "{ref}"}}); 
MERGE (param)-[:HAS_DEVIATION]->(dev);
"""
            for cause_item in causes:
                if cause_item:
                    query += (
                        f'MATCH (c:Cause {{description: "{cause_item}"}})\n'
                        f'MATCH (dev:Deviation {{name: "{deviation}", ref: "{ref}"}})\n'
                        f'MERGE (dev)-[:HAS_CAUSE]->(c);\n'
                    )

            for consequence_item in consequences:
                if consequence_item:
                    query += f'MERGE (con:Consequence {{description: "{consequence_item}"}});\n'
                    query += f'MERGE (dev)-[:LEADS_TO]->(con);\n'

            for safeguard_item in safeguards:
                if safeguard_item:
                    query += f'MERGE (s:Safeguard {{description: "{safeguard_item}"}});\n'
                    query += f'MERGE (dev)-[:HAS_SAFEGUARD]->(s);\n'

            for action_item in actions:
                desc = action_item['description'].replace('"', "'") if isinstance(action_item, dict) else action_item
                assigned_val = action_item['assigned'] if isinstance(action_item, dict) else ""
                ref_val = action_item['ref'] if isinstance(action_item, dict) else ""
                if desc:
                    query += f'MERGE (a:Action {{description: "{desc}", assigned: "{assigned_val}", ref: "{ref_val}"}});\n'
                    query += f'MERGE (dev)-[:HAS_ACTION]->(a);\n'

            cypher_queries.append(query)

    cypher_code = "\n".join(cypher_queries)

    # Print Cypher code to output window
    print(cypher_code)

    # Save Cypher code to file if output_file is specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cypher_code)
        print(f"\nCypher code saved to {output_file}")

    return cypher_code

# Usage example:
# For LLM-powered extraction, set use_llm=True and provide your OpenAI API key from environment variable.
cypher_queries = generate_cypher_from_hazop_csv(
    "HAZOP_006.csv",
    output_file="hazop_kg.cypher",
    use_llm=True,
    openai_api_key=os.getenv("OPENAI_API_KEY")  # <-- Use environment variable
)
#cypher_queries = generate_cypher_from_hazop_csv("HAZOP_006.csv", output_file="hazop_kg.cypher")