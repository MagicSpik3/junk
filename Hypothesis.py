import pandas as pd
import numpy as np

class HypothesisTester:
    def __init__(self, results_df: pd.DataFrame, source_df: pd.DataFrame):
        """
        results_df: The dataframe containing the final results (OO Result, config_OO_Result, etc.)
        source_df: The 'merged_all' dataframe containing the raw sets (sa_initial_codes, clerical_codes)
        """
        self.results_df = results_df
        self.source_df = source_df

    def _get_discrepancy_ids(self, col_legacy: str, col_new: str, mode: str):
        """
        Identifies UIDs based on the comparison mode.
        """
        df = self.results_df
        
        # Helper to treat NaNs as empty strings for comparison
        s1 = df[col_legacy].fillna('').astype(str)
        s2 = df[col_new].fillna('').astype(str)

        if mode == 'Legacy_Blank_New_Found':
            # Case: Legacy missed it (Blank), New found it (True/False)
            mask = (s1 == '') & (s2 != '')
            
        elif mode == 'Legacy_Found_New_Blank':
            # Case: Legacy found it, New missed it
            mask = (s1 != '') & (s2 == '')
            
        elif mode == 'Conflict_True_False':
            # Case: Both found an answer, but they disagree (True vs False)
            mask = (s1 != '') & (s2 != '') & (s1 != s2)
            
        elif mode == 'Both_True':
             mask = (s1 == 'True') & (s2 == 'True')

        else:
            raise ValueError(f"Unknown mode: {mode}")

        return df.loc[mask, 'unique_id']

    def analyze_case(self, case_name: str, col_legacy: str, col_new: str, mode: str):
        """
        Runs the full analysis for a specific column pair and discrepancy mode.
        """
        # 1. Identify UIDs
        uids = self._get_discrepancy_ids(col_legacy, col_new, mode)
        
        if uids.empty:
            print(f"[{case_name}] No records found for mode: {mode}")
            return None

        # 2. Filter Source Data
        subset = self.source_df[self.source_df['unique_id'].isin(uids)].copy()

        # 3. Calculate Stats (Vectorized for speed)
        # Calculate lengths of the sets
        len_sa = subset['sa_initial_codes'].map(len)
        len_cc = subset['clerical_codes'].map(len)
        len_inv = subset['clerical_codes_invalid'].map(len)

        # Create the summary dictionary
        stats = {
            'Test_Case': case_name,
            'Mode': mode,
            'Count': len(subset),
            
            # LLM Stats
            'LLM_Codes_1': (len_sa == 1).sum(),
            'LLM_Codes_Many': (len_sa > 1).sum(),
            
            # Clerical Stats
            'Clerical_Codes_1': (len_cc == 1).sum(),
            'Clerical_Codes_Many': (len_cc > 1).sum(),
            'Clerical_Codes_Huge': (len_cc > 7).sum(), # Explicit check for the "7 item" bug
            
            # Invalid Code Stats
            'Has_Invalid_Code': (len_inv > 0).sum(),
        }

        return stats

    def run_full_diagnostic(self):
        """
        Automatically runs all standard checks for OO, OM, MO, MM.
        """
        prefixes = ['OO', 'OM', 'MO', 'MM']
        modes = ['Legacy_Blank_New_Found', 'Legacy_Found_New_Blank', 'Conflict_True_False']
        
        results = []
        
        for p in prefixes:
            col_legacy = f"{p} Result"
            col_new = f"config_{p}_Result"
            
            # Check if columns exist to avoid errors
            if col_legacy not in self.results_df.columns: continue

            for mode in modes:
                stat = self.analyze_case(p, col_legacy, col_new, mode)
                if stat:
                    results.append(stat)
        
        return pd.DataFrame(results)

# --- USAGE ---
# Assuming 'out_df' and 'merged_all' are already loaded in the notebook

tester = HypothesisTester(out_df, merged_all)

# 1. Run the "One-Click" Report
report_df = tester.run_full_diagnostic()

# Display formatted report
print("Diagnostic Report:")
# Reorder columns for readability
cols = ['Test_Case', 'Mode', 'Count', 'LLM_Codes_Many', 'Clerical_Codes_Many', 'Has_Invalid_Code', 'Clerical_Codes_Huge']
print(report_df[cols].to_string(index=False))

# 2. Run a specific deep dive (like in his original code)
# Example: Investigating MO Disagreements
print("\n--- Deep Dive: MO Conflicts ---")
mo_stats = tester.analyze_case(
    case_name='MO', 
    col_legacy='MO Result', 
    col_new='config_MO_Result', 
    mode='Conflict_True_False'
)
print(mo_stats)
