# HAZOP Modernization: KG Creation and RAG-based Automation

This repository is dedicated to advancing Hazard and Operability (HAZOP) studies through two innovative approaches: creating knowledge graphs from historical data and automating the HAZOP process using advanced AI techniques.

---

## 1. Knowledge Graph (KG) Builder from Existing HAZOP Reports 📂

This component focuses on structuring the invaluable information contained within legacy HAZOP reports. By parsing these documents, we extract key entities (like equipment, deviations, causes, consequences, and safeguards) and their relationships to construct a comprehensive knowledge graph. This structured data can then be used for advanced analytics, querying, and providing deeper insights into plant safety.

* **Purpose**: To convert unstructured text from past HAZOP reports into a structured, queryable knowledge graph.
* **Location**: All relevant scripts and resources for this task can be found in the `KG_builder` folder.

---

## 2. HAZOP Automation using RAG 🤖

This section explores the automation of the HAZOP study process itself. We leverage a **Retrieval-Augmented Generation (RAG)** model, which combines the power of large language models with a knowledge base retrieved from process documentation (like P&IDs and control narratives). The system can intelligently identify potential deviations and predict their consequences, significantly speeding up and enhancing the consistency of HAZOP studies.

* **Purpose**: To automate the generation of HAZOP study outputs by using a RAG model that queries relevant engineering documents.
* **Location**: All code, models, and documentation for the RAG-based HAZOP automation are located in the `HAZOP_using_RAG` folder.
