import csv
import json
import re
from typing import Dict, List, Any

from neo4j import GraphDatabase
import google.generativeai as genai

import config


def normalize_text(value: str) -> str:
    if value is None:
        return ""
    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def load_deviation_rules_from_csv(csv_path: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Parse the Equipment_and_Deviation .csv into a mapping:
      { equipment_category: [ { parameter, guideword, applicability_note } ] }

    The CSV is irregular; this function is resilient to missing/extra columns.
    """
    equipment_to_rules: Dict[str, List[Dict[str, str]]] = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        # Skip header if present by detecting first row's first cell
        rows = list(reader)
        start_idx = 0
        if rows and normalize_text(rows[0][0]).startswith("equipment"):
            start_idx = 1

        current_equipment: str = ""
        current_parameter: str = ""
        for row in rows[start_idx:]:
            # Normalize row to at least 4 columns
            c = list(row) + [""] * (4 - len(row))
            equipment_raw = c[0].strip()
            parameter_raw = c[1].strip()
            guideword_raw = c[2].strip()
            applicability_raw = c[3].strip()

            if equipment_raw:
                current_equipment = equipment_raw
            if parameter_raw:
                current_parameter = parameter_raw

            if not current_equipment or not current_parameter or not guideword_raw:
                continue

            equipment_norm = normalize_text(current_equipment)
            rule = {
                "parameter": current_parameter.strip(),
                "guideword": guideword_raw,
                "applicability": applicability_raw,
            }
            equipment_to_rules.setdefault(equipment_norm, []).append(rule)

    return equipment_to_rules


def get_driver() -> GraphDatabase.driver:
    return GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD))


def fetch_equipment_nodes(session) -> List[Dict[str, str]]:
    query = """
    MATCH (e:Equipment)
    RETURN e.name AS name, e.type AS type
    ORDER BY name
    """
    result = session.run(query)
    return [dict(record) for record in result]


def fetch_equipment_context(session, equipment_name: str) -> Dict[str, Any]:
    """
    Gather useful context about an equipment for the LLM decision:
    - connected sensors, controllers, valves
    - inbound/outbound flows (neighbors and boundary types)
    """
    context: Dict[str, Any] = {"name": equipment_name}

    ctx_queries = {
        "sensors": (
            """
            MATCH (s:Sensor)-[:CONNECTED_TO]->(e:Equipment {name: $name})
            RETURN collect({name: s.name, type: s.type}) AS sensors
            """
        ),
        "controllers": (
            """
            MATCH (c:Controller)-[:CONTROLS]->(t)
            WITH c,t
            MATCH (e:Equipment {name: $name})
            WHERE t = e OR (t)-[:FLOWS_TO*0..1]->(e)
            RETURN collect({name: c.name, type: c.type}) AS controllers
            """
        ),
        "valves": (
            """
            MATCH (v:Valve)-[:FLOWS_TO*0..1]->(e:Equipment {name: $name})
            RETURN collect({name: v.name, type: v.type}) AS valves
            """
        ),
        "inflows": (
            """
            MATCH (n)-[:FLOWS_TO]->(e:Equipment {name: $name})
            RETURN collect(labels(n)) AS inflow_node_labels
            """
        ),
        "outflows": (
            """
            MATCH (e:Equipment {name: $name})-[:FLOWS_TO]->(n)
            RETURN collect(labels(n)) AS outflow_node_labels
            """
        ),
    }

    for key, q in ctx_queries.items():
        rec = session.run(q, name=equipment_name).single()
        if rec is not None:
            context[key] = rec.get(list(rec.keys())[0])
        else:
            context[key] = []

    return context


def configure_llm():
    genai.configure(api_key=config.GEMINI_API_KEY)
    return genai.GenerativeModel(config.GEMINI_MODEL_NAME)


def map_equipment_type_to_csv_category(equipment_type: str) -> List[str]:
    """
    Map graph equipment types to possible CSV equipment categories (normalized).
    Returns list of candidates (first is best guess) to try in rules lookup.
    """
    t = normalize_text(equipment_type)
    candidates: List[str] = [t]

    synonyms = {
        "storage tank": ["storage tank", "tank"],
        "separator": ["separator", "reflux drum/separator", "scrubber"],
        "pump": ["pump"],
        "heat exchanger": ["heat exchanger", "condenser", "vaporiser", "inert gas chiller", "vacuum heater", "cooling water system"],
        "column": ["columns separator", "column"],
        # Add more as needed
    }

    for k, values in synonyms.items():
        if t == k or t in values:
            candidates = values
            break

    return [normalize_text(x) for x in candidates]


def llm_filter_applicable(model, equipment: Dict[str, str], context: Dict[str, Any], candidate_rules: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Ask the LLM to apply applicability rules and return only applicable deviations with rationale.
    Returns list of dicts: {parameter, guideword, rationale}
    """
    if not candidate_rules:
        return []

    system_instructions = (
        "You are a senior process safety engineer performing HAZOP pre-screening.\n"
        "Given an equipment, its P&ID context, and a list of deviation candidates with applicability guidance,\n"
        "return ONLY the deviations that are applicable.\n"
        "Strictly apply the guidance: if guidance says 'Always applicable', mark it applicable;\n"
        "if it describes conditions where it's not applicable, evaluate against the provided context.\n"
        "Respond strictly as minified JSON array, each item with keys: parameter, guideword, rationale. No extra text."
    )

    prompt = {
        "instructions": system_instructions,
        "equipment": {
            "name": equipment.get("name"),
            "type": equipment.get("type"),
        },
        "context": context,
        "candidates": [
            {
                "parameter": r.get("parameter"),
                "guideword": r.get("guideword"),
                "applicability_note": r.get("applicability"),
            }
            for r in candidate_rules
        ],
        "output_schema": [
            {"parameter": "string", "guideword": "string", "rationale": "string"}
        ],
    }

    response = model.generate_content(
        [
            {"role": "user", "parts": [json.dumps(prompt)]}
        ]
    )
    text = (response.text or "").strip()

    # Extract JSON array from response robustly
    try:
        # Sometimes the model can wrap with code-fence; strip if present
        text_clean = re.sub(r"^```(json)?|```$", "", text, flags=re.IGNORECASE | re.MULTILINE).strip()
        data = json.loads(text_clean)
        if isinstance(data, list):
            cleaned: List[Dict[str, Any]] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                param = item.get("parameter")
                guide = item.get("guideword")
                rat = item.get("rationale")
                if param and guide:
                    cleaned.append({
                        "parameter": str(param),
                        "guideword": str(guide),
                        "rationale": str(rat) if rat else "",
                    })
            return cleaned
    except Exception:
        pass

    return []


def write_applicable_to_csv(output_path: str, rows: List[Dict[str, Any]]):
    fieldnames = ["EquipmentName", "EquipmentType", "Parameter", "Guideword", "Rationale"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "EquipmentName": r.get("EquipmentName", ""),
                "EquipmentType": r.get("EquipmentType", ""),
                "Parameter": r.get("Parameter", ""),
                "Guideword": r.get("Guideword", ""),
                "Rationale": r.get("Rationale", ""),
            })


def main():
    # Load deviation rules
    rules_by_equipment = load_deviation_rules_from_csv("Context for RAG\\Equipment_and_Deviation.csv")

    # Configure LLM
    model = configure_llm()

    all_output_rows: List[Dict[str, Any]] = []

    # Connect to Neo4j
    driver = get_driver()
    try:
        with driver.session() as session:
            equipments = fetch_equipment_nodes(session)
            for eq in equipments:
                name = eq.get("name", "")
                eq_type = eq.get("type", "")
                category_candidates = map_equipment_type_to_csv_category(eq_type)

                # Merge all candidate rules from the CSV categories
                candidate_rules: List[Dict[str, str]] = []
                for cat in category_candidates:
                    if cat in rules_by_equipment:
                        candidate_rules.extend(rules_by_equipment[cat])

                if not candidate_rules:
                    # Try a direct match on the raw type as fallback
                    raw_norm = normalize_text(eq_type)
                    candidate_rules = rules_by_equipment.get(raw_norm, [])

                if not candidate_rules:
                    continue

                # Fetch P&ID context for applicability evaluation
                context = fetch_equipment_context(session, name)

                applicable = llm_filter_applicable(model, eq, context, candidate_rules)
                for item in applicable:
                    all_output_rows.append({
                        "EquipmentName": name,
                        "EquipmentType": eq_type,
                        "Parameter": item["parameter"],
                        "Guideword": item["guideword"],
                        "Rationale": item.get("rationale", ""),
                    })

    finally:
        driver.close()

    # Write results
    output_file = config.APPLICABLE_DEVIATIONS_PATH
    write_applicable_to_csv(output_file, all_output_rows)
    print(f"Wrote {len(all_output_rows)} applicable deviations to {output_file}")


if __name__ == "__main__":
    main()

