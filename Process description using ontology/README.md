# Automated P&ID Process Description Generator using Ontologies

This project provides a sophisticated framework for automatically generating detailed, human readable process descriptions for key chemical engineering equipment specifically **Reactors** and **Storage Tanks** by analyzing data from a Piping and Instrumentation Diagram (P&ID) stored in a Neo4j graph database.

The core innovation is the integration of a formal knowledge base, an **OWL Ontology**, to enrich the raw P&ID data with engineering context, definitions, and relationships. This turns a simple "what is connected to what" analysis into a descriptive "how and why it works" summary.

## 📂 Folder Structure

The project is organized into a logical structure to separate the source code, knowledge bases (ontologies), and output results.
```
Process description using ontology/
├── Ontology/
│   ├── Reactor Ontology.rdf
│   └── Storage Tank Ontology.rdf
├── Results/
│   ├── reactor_descriptions.txt
│   └── storage_tank_descriptions.txt
├── Reactor_description_generator.py
├── Storage_tank_description_generator.py
└── README.md
```

* **`Ontology/`**: Contains the OWL/RDF files that serve as the knowledge base.
    * `Reactor Ontology.rdf`: Defines the concepts, properties, and relationships specific to chemical reactors (e.g., `CSTR`, `PFR`, `Agitator`, `Catalyst`).
    * `Storage Tank Ontology.rdf`: Defines concepts for storage tanks (e.g., `Fixed_roof`, `Floating_roof`, `Bund_Wall`, `Blanket_Gas_System`).
* **`Results/`**: The default output directory where the generated text descriptions are saved.
* **`*.py` files**: The main Python scripts that perform the analysis and description generation.
* **`README.md`**: This file.

## 🎯 Project Purpose

Interpreting complex P&IDs is a time-consuming and expertise-intensive task for chemical and process engineers. The goal of this project is to automate this process by:

1.  **Extracting Data**: Connecting to a Neo4j database that models a P&ID as a graph of equipment, pipelines, and instruments.
2.  **Enriching with Knowledge**: Using an ontology to understand what the components *are* and how they *should* function. For example, the ontology defines that a `Rupture_Disc` is a type of `Pressure_Relief` device, which is a `Safety_System`.
3.  **Analyzing Relationships**: Intelligently traversing the graph to identify process flows, control loops, safety systems, and utilities.
4.  **Generating Reports**: Producing structured, easy-to-read text files that describe each piece of equipment, its function, its connections, and its role in the overall process.

This tool is invaluable for process documentation, operator training, safety analysis, and knowledge management.

## 🧠 Core Logic and Workflow

Both the `Reactor_description_generator.py` and `Storage_tank_description_generator.py` scripts follow a similar multi-stage logic:



#### 1. Data Connection and Extraction

* **Neo4j Connection**: The scripts establish a connection to a running Neo4j instance using the provided credentials.
* **Graph Fetching**: A Cypher query is executed to pull all nodes (equipment, instruments, etc.) and their relationships from the database into the script's memory.

#### 2. Ontology Parsing

* **Load Knowledge**: The `rdflib` library is used to load and parse the corresponding `.rdf` ontology file (`Reactor Ontology.rdf` for the reactor script, `Storage Tank Ontology.rdf` for the tank script).
* **Extract Concepts**: The script extracts key information, such as class hierarchies (e.g., `CSTR` is a subclass of `Continuous` reactor ), object properties (e.g., `has_inlet` connects a `Reactor` to an `Inlet` ), and descriptive comments associated with each concept.

#### 3. Equipment Identification and Analysis

* **Identify Targets**: The `ReactorAnalyzer` / `StorageTankAnalyzer` class scans through all nodes fetched from Neo4j to identify the primary equipment of interest (reactors or storage tanks) based on their properties or labels.
* **Connection Classification**: This is the most critical logic. For each identified piece of equipment, the script analyzes all its direct connections. It uses heuristics based on the connected node's type, labels, and the relationship type to categorize each connection as one of the following:
    * **Inlet/Outlet Stream**: A process flow line.
    * **Instrument**: A sensor, transmitter, or controller.
    * **Safety Device**: An emergency shutdown valve or pressure relief device.
    * **Utility**: A connection for steam, nitrogen, etc.
    * **Internal Component**: For reactors, it specifically looks for components defined in the ontology like `Agitator` or `Internal_Baffles`.

#### 4. Advanced Graph Traversal

* **Endpoint Resolution**: The scripts recognize that a reactor isn't just connected to a "pipe"; it's connected *through* a series of pipes, valves, and fittings to another major piece of equipment. The `collect_stream_end_equipment` function intelligently traverses the graph upstream or downstream to find the true source or destination equipment, providing a much more meaningful description.
* **Chemical Backtracking**: A dedicated Cypher query is run to trace process lines far upstream to find source `Chemical` nodes and far downstream to find sink `Chemical` nodes. This allows the script to infer what substances are being fed into and removed from the equipment.
* **Control Loop Inference**: The scripts look for a specific pattern: an **Instrument** (sensor) connected to a **Controller**, which is in turn connected to an **Actuator** (like a `Control_Valve`). By identifying this `Sensor -> Controller -> Actuator` chain, it can infer and describe the function of an automated control loop.

#### 5. Description Generation

* **Structured Assembly**: A final `Generator` class takes all the analyzed data—the equipment's properties, its classified connections, the resolved endpoints, the inferred chemicals, and the control loops—and assembles it into a structured text report.
* **Ontology Integration**: During generation, the script pulls in the descriptive comments from the parsed ontology to explain the *function* of different components. For example, when it finds a `Bund_Wall`, it can add the ontology's definition: "physical barriers built around a tank to provide secondary containment in the event of a primary containment failure".
* **File Output**: The final string is written to a `.txt` file in the `Results/` folder.