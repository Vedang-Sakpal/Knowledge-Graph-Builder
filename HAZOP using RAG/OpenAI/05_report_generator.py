# UPDATED: This script now reads from the intermediate JSON file instead of querying Neo4j.

import config
import pandas as pd
import json

class ReportGenerator:
    def __init__(self):
        # No database connection needed anymore
        pass

    def load_data_from_json(self, json_path):
        """Loads the HAZOP data from the intermediate JSON file."""
        print(f"Loading HAZOP data from {json_path}...")
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            print(f"Error: {json_path} not found. Please run the analysis script (04) first.")
            return None
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {json_path}. The file may be empty or corrupt.")
            return None

    def generate_excel_report(self, hazop_data, output_path):
        """
        Processes the fetched data and writes it to a formatted Excel file.
        """
        if not hazop_data:
            print("No HAZOP data found to generate a report.")
            return
        print(f"Generating Excel report at {output_path}...")
        
        def format_list(items):
            # Ensure items is a list before trying to iterate
            if not isinstance(items, list):
                return ""
            return "\n".join([f"- {i.get('description', '')} (Conf: {i.get('confidenceLevel', 0):.2f}, Src: {i.get('source', 'N/A')})" for i in items])
        
        flat_data = [{
            "Node": item['node'],
            "Guideword": item['guideword'],
            "Parameter": item['parameter'],
            "Deviation": item['deviation'],
            "Causes": format_list(item['causes']),
            "Consequences": format_list(item['consequences']),
            "Safeguards": format_list(item['safeguards'])
        } for item in hazop_data]
        
        df = pd.DataFrame(flat_data)
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='HAZOP Worksheet', index=False)
            workbook, worksheet = writer.book, writer.sheets['HAZOP Worksheet']
            header_fmt = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'fg_color': '#D7E4BC', 'border': 1})
            cell_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top'})
            low_conf_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_fmt)
            worksheet.set_column('A:A', 40, cell_fmt)
            worksheet.set_column('B:D', 15, cell_fmt)
            worksheet.set_column('E:G', 50, cell_fmt)
            worksheet.freeze_panes(1, 0)
            worksheet.conditional_format(f'E2:G{len(df)+1}', {'type': 'text', 'criteria': 'containing', 'value': '(Conf: 0.', 'format': low_conf_fmt})
        print("Excel report generated successfully.")

def main():
    reporter = ReportGenerator()
    hazop_data = reporter.load_data_from_json(config.HAZOP_RESULTS_JSON_PATH)
    if hazop_data:
        reporter.generate_excel_report(hazop_data, config.EXCEL_REPORT_PATH)
    print("Phase 5: Report Generation complete.")

if __name__ == "__main__":
    main()
