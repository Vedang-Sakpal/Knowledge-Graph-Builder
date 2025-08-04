# UPDATED: This script now reads from the intermediate JSON file instead of querying Neo4j.

import config
import pandas as pd
import json

class ReportGenerator:
    """
    A class responsible for generating a formatted Excel report from HAZOP analysis data.
    It reads data from a JSON file, processes it, and writes it to an Excel worksheet.
    """
    def __init__(self):
        # The constructor is simple because this class no longer needs a direct
        # database connection; it works with a file instead.
        pass

    def load_data_from_json(self, json_path):
        """
        Loads the HAZOP data from the intermediate JSON file created by the analysis script.
        
        Args:
            json_path (str): The file path for the input JSON file.

        Returns:
            list: A list of dictionaries containing the HAZOP data, or None if an error occurs.
        """
        print(f"Loading HAZOP data from {json_path}...")
        try:
            # Open the JSON file in read mode
            with open(json_path, 'r') as f:
                # Load the data from the file into a Python list
                data = json.load(f)
            return data
        except FileNotFoundError:
            # Handle the error if the input file does not exist
            print(f"Error: {json_path} not found. Please run the analysis script (04) first.")
            return None
        except json.JSONDecodeError:
            # Handle the error if the file is not a valid JSON file
            print(f"Error: Could not decode JSON from {json_path}. The file may be empty or corrupt.")
            return None

    def generate_excel_report(self, hazop_data, output_path):
        """
        Processes the raw HAZOP data and writes it to a well-formatted Excel file.

        Args:
            hazop_data (list): The list of HAZOP data loaded from the JSON file.
            output_path (str): The file path for the output Excel report.
        """
        if not hazop_data:
            # If there's no data, print a message and exit the function
            print("No HAZOP data found to generate a report.")
            return
        
        print(f"Generating Excel report at {output_path}...")
        
        # --- Helper Function for Formatting ---
        def format_list(items):
            """
            A nested helper function to format lists of causes, consequences, or safeguards
            into a single, human-readable string with newlines for use in an Excel cell.
            """
            # Check if the input is a valid list to prevent errors
            if not isinstance(items, list):
                return ""
            # Format each item in the list into a standard string format
            return "\n".join([f"- {i.get('description', '')} (Conf: {i.get('confidenceLevel', 0):.2f}, Src: {i.get('source', 'N/A')})" for i in items])
        
        # --- Data Transformation ---
        # Convert the raw list of dictionaries into a "flat" structure suitable for a DataFrame.
        # Each dictionary in this new list will represent one row in the Excel sheet.
        flat_data = [{
            "Node": item['node'],
            "Guideword": item['guideword'],
            "Parameter": item['parameter'],
            "Deviation": item['deviation'],
            "Causes": format_list(item['causes']),
            "Consequences": format_list(item['consequences']),
            "Safeguards": format_list(item['safeguards'])
        } for item in hazop_data]
        
        # Create a pandas DataFrame from the flattened data
        df = pd.DataFrame(flat_data)
        
        # --- Excel Formatting and Writing ---
        # Use ExcelWriter with the 'xlsxwriter' engine for advanced formatting
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            # Write the DataFrame to an Excel sheet without the default pandas index
            df.to_excel(writer, sheet_name='HAZOP Worksheet', index=False)
            
            # Get the workbook and worksheet objects for direct formatting
            workbook, worksheet = writer.book, writer.sheets['HAZOP Worksheet']
            
            # Define various cell formats for a professional look
            header_fmt = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'fg_color': '#D7E4BC', 'border': 1})
            cell_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top'})
            low_conf_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'}) # For low confidence items

            # Write the header row using the defined header format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_fmt)
            
            # Set the column widths for better readability
            worksheet.set_column('A:A', 40, cell_fmt)  # Node column
            worksheet.set_column('B:D', 15, cell_fmt)  # Guideword, Parameter, Deviation
            worksheet.set_column('E:G', 50, cell_fmt)  # Causes, Consequences, Safeguards
            
            # Freeze the top row so the headers are always visible when scrolling
            worksheet.freeze_panes(1, 0)
            
            # Apply conditional formatting to highlight cells containing low-confidence findings
            worksheet.conditional_format(f'E2:G{len(df)+1}', {'type': 'text', 'criteria': 'containing', 'value': '(Conf: 0.', 'format': low_conf_fmt})
            
        print("Excel report generated successfully.")

def main():
    """
    The main function that orchestrates the report generation process.
    """
    # Create an instance of the ReportGenerator
    reporter = ReportGenerator()
    
    # Load the data from the JSON file specified in the config
    hazop_data = reporter.load_data_from_json(config.HAZOP_RESULTS_JSON_PATH)
    
    # If data was loaded successfully, generate the Excel report
    if hazop_data:
        reporter.generate_excel_report(hazop_data, config.EXCEL_REPORT_PATH)
    
    print("Phase 5: Report Generation complete.")

# Standard Python entry point to run the main function when the script is executed
if __name__ == "__main__":
    main()
