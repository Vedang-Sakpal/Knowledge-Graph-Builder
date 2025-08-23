# NEW SCRIPT: This script compares the generated HAZOP report with the original report.

import config
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re

class VerificationEngine:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Verification Engine initialized.")

    def load_reports(self):
        """Loads the generated and original HAZOP reports."""
        try:
            # Load the AI-generated report from the Excel file
            self.generated_df = pd.read_excel(config.EXCEL_REPORT_PATH, sheet_name='HAZOP Worksheet').fillna('')
            print(f"Successfully loaded generated report from {config.EXCEL_REPORT_PATH}")
        except FileNotFoundError:
            print(f"Error: Generated report not found at {config.EXCEL_REPORT_PATH}")
            return False

        try:
            # Load the original report from the CSV file
            self.original_df = pd.read_csv(config.ORIGINAL_HAZOP_REPORT_PATH).fillna('')
            print(f"Successfully loaded original report from {config.ORIGINAL_HAZOP_REPORT_PATH}")
        except FileNotFoundError:
            print(f"Error: Original report not found at {config.ORIGINAL_HAZOP_REPORT_PATH}")
            return False
        
        return True

    def preprocess_text(self, text):
        """Cleans and normalizes a single string."""
        if not isinstance(text, str):
            return ""
        # Remove list markers, convert to lowercase, and strip whitespace
        text = re.sub(r'^\s*-\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\(Conf:.*?\)', '', text) # Remove confidence scores
        return text.lower().strip()

    def split_and_clean_column(self, series):
        """Splits a series of newline-separated strings into a list of cleaned strings."""
        return series.apply(lambda x: [self.preprocess_text(item) for item in str(x).split('\n') if self.preprocess_text(item)])

    def verify(self):
        """Performs the full verification process."""
        if not self.load_reports():
            return

        # Preprocess the original report
        self.original_df.rename(columns={'Hazard': 'Deviation', 'Causes': 'Causes_orig', 'Consequences': 'Consequences_orig', 'Likelihood and Prevention': 'Safeguards_orig'}, inplace=True)
        self.original_df['Deviation_clean'] = self.original_df['Deviation'].apply(self.preprocess_text)
        self.original_df['Causes_list'] = self.split_and_clean_column(self.original_df['Causes_orig'])
        self.original_df['Consequences_list'] = self.split_and_clean_column(self.original_df['Consequences_orig'])
        self.original_df['Safeguards_list'] = self.split_and_clean_column(self.original_df['Safeguards_orig'])

        # Preprocess the generated report
        self.generated_df['Deviation_clean'] = self.generated_df['Deviation'].apply(self.preprocess_text)
        self.generated_df['Causes_list'] = self.split_and_clean_column(self.generated_df['Causes'])
        self.generated_df['Consequences_list'] = self.split_and_clean_column(self.generated_df['Consequences'])
        self.generated_df['Safeguards_list'] = self.split_and_clean_column(self.generated_df['Safeguards'])

        # Create embeddings for the deviations to match rows
        original_dev_embeddings = self.model.encode(self.original_df['Deviation_clean'].tolist())
        generated_dev_embeddings = self.model.encode(self.generated_df['Deviation_clean'].tolist())

        total_similarity = {'Causes': [], 'Consequences': [], 'Safeguards': []}
        total_recall = {'Causes': [], 'Consequences': [], 'Safeguards': []}

        # Match each generated row to the most similar original row
        for i, gen_embedding in enumerate(generated_dev_embeddings):
            similarities = cosine_similarity([gen_embedding], original_dev_embeddings)[0]
            best_match_idx = np.argmax(similarities)
            
            # Only consider it a match if the deviation similarity is high
            if similarities[best_match_idx] > 0.7:
                gen_row = self.generated_df.iloc[i]
                orig_row = self.original_df.iloc[best_match_idx]

                for cat in ['Causes', 'Consequences', 'Safeguards']:
                    gen_items = gen_row[f'{cat}_list']
                    orig_items = orig_row[f'{cat}_list']
                    
                    if orig_items: # Only calculate if there's something to compare against
                        sim = self.calculate_similarity(gen_items, orig_items)
                        rec = self.calculate_recall(gen_items, orig_items)
                        total_similarity[cat].append(sim)
                        total_recall[cat].append(rec)

        print("\n======================================================")
        print("          HAZOP Verification Report                 ")
        print("======================================================")
        for cat in ['Causes', 'Consequences', 'Safeguards']:
            avg_sim = np.mean(total_similarity[cat]) if total_similarity[cat] else 0
            avg_rec = np.mean(total_recall[cat]) if total_recall[cat] else 0
            print(f"\n--- Category: {cat} ---")
            print(f"  Average Semantic Similarity: {avg_sim:.2%}")
            print(f"  Average Recall: {avg_rec:.2%}")
        print("\n======================================================")

    def calculate_similarity(self, generated_items, original_items):
        """Calculates how well the generated items match the original items."""
        if not generated_items or not original_items:
            return 0.0
        
        gen_embed = self.model.encode(generated_items)
        orig_embed = self.model.encode(original_items)
        
        sim_matrix = cosine_similarity(gen_embed, orig_embed)
        # For each generated item, find its best match in the original set
        max_sim_scores = np.max(sim_matrix, axis=1)
        return np.mean(max_sim_scores)

    def calculate_recall(self, generated_items, original_items, threshold=0.75):
        """Calculates what percentage of original items were 'found' by the AI."""
        if not original_items:
            return 1.0
        if not generated_items:
            return 0.0
            
        orig_embed = self.model.encode(original_items)
        gen_embed = self.model.encode(generated_items)
        
        sim_matrix = cosine_similarity(orig_embed, gen_embed)
        # For each original item, see if it has at least one good match in the generated set
        found_count = np.sum(np.max(sim_matrix, axis=1) > threshold)
        return found_count / len(original_items)

def main():
    verifier = VerificationEngine()
    verifier.verify()

if __name__ == "__main__":
    main()
