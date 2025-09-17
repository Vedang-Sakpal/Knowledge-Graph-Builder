# HAZOP using RAG

This project implements an **Ontology-Driven HAZOP (Hazard and Operability) analysis automation pipeline** using a **Retrieval-Augmented Generation (RAG)** approach.  
It combines structured process data, a formal HAZOP ontology, chemical MSDS files, and historical HAZOP datasets to generate **highly detailed and professional HAZOP reports**.

---

## 📂 Folder Structure

```
HAZOP using RAG/
│
├── MSDS/                                         # Material Safety Data Sheets for chemicals
│   ├── <chemical_name>.pdf / .txt
│
├── P&ID/                                         # Digitalized P&ID Cypher files for Neo4j
│   ├── <pid_file>.cypher
│
├── Context/                                      # Normalized knowledge extracted from 20 HAZOP reports
│   ├── Parameter_and_guideword.csv
│   ├── Causes.csv
│   ├── Consequences.csv
│   ├── Safeguard.csv
│
├── Process Description/                          # Process description in Markdown
│   ├── <process_description>.md
│   ├── <process_description>.txt                 # Process description generated using storage tank ontology only
│
├── Results/                                      # Output HAZOP reports and Generated Process Description 
│   ├── HAZOP_Analysis_Equipment_name.xlsx
│   ├── HAZOP_Analysis_Equipment_name.json
│   ├── Generated_process_description.md
│   ├── Applicable_deviations.md
│
├── HAZOP_Ontology_CLEAN.rdf                      # Formal RDF ontology for HAZOP
│
├── config.py                                     # Conatains the API key and credentials for connetcing Neo4j database and path for all files
├── 01_prasing_P&ID.py                            # Clear the existing graph database and load the P&ID 
├── 02_ontology_loader.py                         # Loads ontology & applies schema constraints in Neo4j
├── 03_semantic_enrichment.py                     # Enriches graph with chemical/MSDS data using LLM
├── 04_equipment_node.py                          # Creates one HAZOP node per equipment
├── 05_Understanding_process_using_LLM.py         # Using the basic knowledge process description generate more specific process description
├── 06_Generate_applicbale_deviations.py          # Generates equipment specific deviatoins from the equipment and deviation csv file  
├── 07_HAZOP_analysis.py                          # Conduct HAZOP analysis based on certain rules
├── 08_verify_accuracy.py                         # Verify the generated report with the actual report 
├── main.py                                       # Orchestrates the full pipeline
├── requirements.txt                              # Python dependencies
└── README.md                                     # Project documentation (this file)
```

---

## 🧠 Project Workflow

1. **P&ID Parsing (`01_parsing_P&ID.py`)**  
   - Clears existing graph data and loads P&ID information from Cypher files
   - Establishes process flow relationships between equipment
  
2. **Ontology Loading (`02_ontology_loader.py`)**  
   - Loads `HAZOP_Ontology_CLEAN.rdf` into Neo4j and applies class-based uniqueness constraints.

3. **Semantic Enrichment (`03_semantic_enrichment.py`)**  
   - Uses Gemini LLM to extract and normalize chemical/MSDS data.  
   - Populates Neo4j with synonyms, hazards, and operating parameters.

4. **Node Creation**   
   - **Per Equipment** (`04_equipment_node.py`): One node per equipment.  

5. **Process Understanding (`05_Understanding_process_using_LLM.py`)**  
   - Enhances basic process descriptions using LLM capabilities
   - Generates detailed operational parameters and scenarios

6. **Deviation Generation (`06_Generate_applicable_deviations.py`)**  
   - Generates equipment-specific deviations from `Equipment_and_Deviations.csv`. 
   - Matches equipment parameters with guidewords and store them in `Applicable_deviation.csv`.

7. **HAZOP Analysis (`07_HAZOP_analysis.py`)**  
   - Get the deviation from the `Applicable_deviation.csv` generated before this step.     
   - Uses RAG with LLM to produce structured analysis.  
   - Writes results to Neo4j and saves intermediate JSON. 
   - Converts JSON into a professionally formatted `.xlsx` HAZOP report.

8. **Accuracy Verification (`08_verify_accuracy.py`)**  
   - Compares generated report against original using semantic similarity and recall.

9.  **Pipeline Execution (`main.py`)**  
    - Runs all stages in sequence, checks prerequisites, and saves final output in `Results/`.

---

## ⚙️ Installation

```bash
pip install -r requirements.txt
```

Dependencies include:
- `neo4j`
- `pandas`
- `xlsxwriter`
- `sentence-transformers`
- `faiss-cpu`
- `rdflib`
- `tqdm`
- `openai` or `google-generativeai` (for LLM integration)

---

## 🚀 Running the Pipeline

1. **Ensure prerequisites are met**:
   - Neo4j database is running and P&ID Cypher files are loaded.
   - MSDS, Context CSVs, and Process Descriptions are available.
   - API keys and file paths are set in `config.py`.

2. **Run the pipeline**:
   ```bash
   python main.py
   ```

3. **View results**:
   - `Results/HAZOP_Analysis_Equipment_name.xlsx` (Excel)
   - `Results/HAZOP_Analysis_Equipment_name.json` (JSON)
   - `Results/Generated_process_description.dm` (Markdowm)
   - `Results/Applicable_deviations.csv` (csv)
   - 

---

## 📌 Notes
- The RAG retrieval ensures historical consistency in cause/consequence/safeguard recommendations.
- API calls are cached to reduce cost and improve speed.
- Verification is optional but recommended for QA.

---

## 🛡️ Disclaimer
This system assists in **drafting** HAZOP reports.  
All generated content must be reviewed and approved by certified process safety engineers before use.

---
