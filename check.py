import pandas as pd
import numpy as np

def get_mismatch_ids(df: pd.DataFrame, prefixes: list = None) -> dict:
    """
    Identifies unique_ids where model results diverge.
    
    Logic:
    - Legacy_False_vs_Config_Mismatch: Legacy is False, Config is NOT False (True or NaN)
    - Legacy_True_vs_Config_Mismatch: Legacy is True, Config is NOT True (False or NaN)
    """
    if prefixes is None:
        prefixes = ["OO", "OM", "MO", "MM"]
        
    results = {}

    for p in prefixes:
        # Construct dynamic column names
        legacy_col = f"{p} Result"
        config_col = f"config_{p}_Result"
        
        # Safety check: ensure columns exist
        if legacy_col not in df.columns or config_col not in df.columns:
            print(f"Warning: Columns for prefix '{p}' not found. Skipping.")
            continue
            
        # ---------------------------------------------------------
        # Scenario 1: Legacy says FALSE, but Config says True or NaN
        # ---------------------------------------------------------
        # We use explicit comparison (== False) to handle NaNs correctly.
        # (NaN == False) evaluates to False, so NaNs in legacy are safely ignored here.
        mask_false_mismatch = (
            (df[legacy_col] == False) & 
            (df[config_col] != False)
        )
        
        ids_false_mismatch = df.loc[mask_false_mismatch, 'unique_id'].tolist()

        # ---------------------------------------------------------
        # Scenario 2: Legacy says TRUE, but Config says False or NaN
        # ---------------------------------------------------------
        mask_true_mismatch = (
            (df[legacy_col] == True) & 
            (df[config_col] != True)
        )
        
        ids_true_mismatch = df.loc[mask_true_mismatch, 'unique_id'].tolist()

        # Store results
        results[p] = {
            "Legacy_False_vs_Config_Mismatch": ids_false_mismatch,
            "Legacy_True_vs_Config_Mismatch": ids_true_mismatch
        }

    return results




# Create the test data matching your prompt
data = {
    'unique_id': ['EV000025', 'EV000027', 'EV000057', 'EV000064', 'EV000099'],
    'OO Result': [False, np.nan, np.nan, np.nan, np.nan],
    'OM Result': [False, np.nan, np.nan, np.nan, np.nan],
    'MO Result': [False, np.nan, True, True, np.nan],
    'MM Result': [False, True, True, True, True],
    
    # Config columns
    'config_OO_Result': [False, np.nan, np.nan, np.nan, np.nan],
    'config_OM_Result': [False, np.nan, np.nan, np.nan, np.nan],
    'config_MO_Result': [False, True, True, True, True], # Note: EV000027 is True here, but NaN in legacy
    'config_MM_Result': [False, True, True, True, True]
}

df_test = pd.DataFrame(data)

# Run the function
mismatches = get_mismatch_ids(df_test)

# Print specific mismatch for MO Result
# This should catch EV000027 if we were looking for mismatch from NaN, 
# BUT based on strict logic: Legacy(NaN) == False is False. So it ignores it.
# To catch Legacy(False) -> Config(True):
print("Mismatches found:", mismatches)
