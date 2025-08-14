# HAZOP using RAG

This project implements an **Ontology-Driven HAZOP (Hazard and Operability) analysis automation pipeline** using a **Retrieval-Augmented Generation (RAG)** approach.  
It combines structured process data, a formal HAZOP ontology, chemical MSDS files, and historical HAZOP datasets to generate **highly detailed and professional HAZOP reports**.

---

## 📂 Folder Structure

```
HAZOP using RAG/
│
├── MSDS/                               # Material Safety Data Sheets for chemicals
│   ├── <chemical_name>.pdf / .txt
│
├── P&ID/                               # Digitalized P&ID Cypher files for Neo4j
│   ├── <pid_file>.cypher
│
├── Context/                            # Normalized knowledge extracted from 20 HAZOP reports
│   ├── Parameter_and_guideword.csv
│   ├── Causes.csv
│   ├── Consequences.csv
│   ├── Safeguard.csv
│
├── Process Description/                # Process description in Markdown
│   ├── <process_description>.md
│
├── Results/                            # Output reports
│   ├── HAZOP_Report_Generated.xlsx
│   ├── hazop_results.json
│
├── HAZOP_Ontology_CLEAN.rdf            # Formal RDF ontology for HAZOP
│
├── config.py                           # Conatains the API key and credentials for connetcing Neo4j database and path for all files
├── 01_ontology_loader.py               # Loads ontology & applies schema constraints in Neo4j
├── 02_semantic_enrichment.py           # Enriches graph with chemical/MSDS data using LLM
├── 03_equipment_node.py                # Creates one HAZOP node per equipment
├── 03_manual_noding.py                 # Interactive manual node selection
├── 04_hazop_analysis_engine.py         # RAG-based deviation, cause, consequence, safeguard generation
├── 05_report_generator.py              # Generates formatted Excel report from JSON
├── 06_verify_accuracy.py               # Compares generated report with original for accuracy
├── main.py                             # Orchestrates the full pipeline
├── requirements.txt                    # Python dependencies
└── README.md                           # Project documentation (this file)
```

---

## 🧠 Project Workflow

1. **Ontology Loading (`01_ontology_loader.py`)**  
   - Loads `HAZOP_Ontology_CLEAN.rdf` into Neo4j and applies class-based uniqueness constraints.

2. **Semantic Enrichment (`02_semantic_enrichment.py`)**  
   - Uses Gemini LLM to extract and normalize chemical/MSDS data.  
   - Populates Neo4j with synonyms, hazards, and operating parameters.

3. **Node Creation**   
   - **Per Equipment** (`03_equipment_node.py`): One node per equipment.  
   - **Manual** (`03_manual_noding.py`): User selects components to define nodes.

1. **HAZOP Analysis (`04_hazop_analysis_engine.py`)**  
   - Generates deviations from `Parameter_and_guideword.csv`.  
   - Retrieves relevant causes, consequences, safeguards from historical CSVs.  
   - Uses RAG with LLM to produce structured analysis.  
   - Writes results to Neo4j and saves intermediate JSON.

2. **Report Generation (`05_report_generator.py`)**  
   - Converts JSON into a professionally formatted `.xlsx` HAZOP report.

3. **Accuracy Verification (`06_verify_accuracy.py`)**  
   - Compares generated report against original using semantic similarity and recall.

4. **Pipeline Execution (`main.py`)**  
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
   - `Results/HAZOP_Report_Generated.xlsx` (Excel)
   - `Results/hazop_results.json` (JSON)

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
