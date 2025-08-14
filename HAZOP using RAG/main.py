# UPDATED: This script is now corrected to properly handle the interactive manual noding step.

import os
import subprocess
import config

def run_script(script_name, interactive=False):
    """
    Helper function to run a python script and handle errors.
    It can now run scripts in interactive or non-interactive mode.
    """
    print(f"--- Running {script_name} ---")
    try:
        if interactive:
            # For interactive scripts, we run the process without capturing output,
            # allowing it to use the main terminal for input and output. This is the fix.
            result = subprocess.run(['python', script_name], check=True, text=True)
        else:
            # For non-interactive scripts, we capture the output to print it upon completion.
            result = subprocess.run(['python', script_name], check=True, capture_output=True, text=True)
            print(result.stdout)
        
        print(f"--- Finished {script_name} successfully ---")
        return True
    except subprocess.CalledProcessError as e:
        print(f"!!! Error running {script_name} !!!")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print(f"!!! Error: {script_name} not found. Make sure all scripts are in the same directory. !!!")
        return False

def main():
    """Main function to execute the HAZOP automation pipeline."""
    print("======================================================")
    print("  Ontology-Driven HAZOP Generation Framework          ")
    print("======================================================")
    print("\nNOTE: This pipeline assumes you have already loaded your\nP&ID data into the Neo4j database.\n")

    # The pipeline now explicitly defines which script requires user interaction.
    pipeline_scripts = {
        "01_ontology_loader.py": False,
        "02_semantic_enrichment.py": False,
        "03_equipment_node.py": False,
        #"03_automatic_noding.py": False,  
        "04_hazop_analysis_engine.py": False,
        "05_report_generator.py": False,
        "06_verify_accuracy.py": False
    }

    # Execute each script in the pipeline, passing the interactive flag.
    for script, is_interactive in pipeline_scripts.items():
        if not run_script(script, interactive=is_interactive):
            print(f"\nPipeline stopped due to an error in {script}.")
            break
        print("\n")

    print("======================================================")
    print("          Pipeline execution complete.                ")
    print("======================================================")
    print(f"Check the Neo4j database for the HAZOP Knowledge Graph.")
    print(f"Check the project directory for the generated '{config.EXCEL_REPORT_PATH}' file.")

if __name__ == "__main__":
    # Ensure necessary files and directories exist before starting
    required_files = [
        config.ONTOLOGY_FILE_PATH,
        config.CAUSES_CSV_PATH,
        config.CONSEQUENCES_CSV_PATH,
        config.SAFEGUARDS_CSV_PATH,
        config.PARAMETER_GUIDEWORD_CSV_PATH
    ]
    
    files_missing = False
    for f in required_files:
        if not os.path.exists(f):
            print(f"Error: Required file not found at path: {f}")
            files_missing = True
            
    if not os.path.isdir(config.MSDS_DIRECTORY_PATH):
        print(f"Error: MSDS directory not found at path: {config.MSDS_DIRECTORY_PATH}")
        files_missing = True

    if not files_missing:
        main()
    else:
        print("\nPlease ensure all required files and directories are present and paths in config.py are correct.")