from rdflib import Graph, URIRef
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
import os

def merge_ontologies(main_file_path, output_file):
    # Create a new graph
    merged_graph = Graph()
    
    # Process the main file and all imports recursively
    def process_file(file_path):
        g = Graph()
        g.parse(file_path)
        
        # Add all triples to merged graph
        for triple in g:
            merged_graph.add(triple)
            
        # Find import statements and process them
        for s, p, o in g.triples((None, URIRef("http://www.w3.org/2002/07/owl#imports"), None)):
            import_path = str(o).replace("file://", "")
            if os.path.exists(import_path):
                process_file(import_path)
    
    process_file(main_file_path)
    
    # Save the merged ontology
    merged_graph.serialize(destination=output_file, format='xml')

# Usage
merge_ontologies("ontology/OntoCAPE/OntoCAPE.owl", "merged_ontology.owl")