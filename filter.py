import pandas as pd
import numpy as np
import os
import logging

# --- Configuration ---
# Point this to your main data file (e.g., unit_test_all.csv)
SOURCE_FILE = "unit_test_all.csv"
OUTPUT_DIR = "test_subsets/"

# Define the columns to check, based on your SA-160c config
CLERICAL_COLS = [f"CC_{i}" for i in range(1, 4)]  # CC_1, CC_2, CC_3
MODEL_COLS = [f"SA_{i}" for i in range(1, 6)]    # SA_1 ... SA_5
ALL_LABEL_COLS = CLERICAL_COLS + MODEL_COLS
ID_COL = "unique_id"

# Define what we consider "empty" for counting purposes
# These are based on the INVALID_VALUES in sic_codes.py and common NaNs
EMPTY_VALUES = [
    "", ".", " ", np.nan, None, "NAN", "NaN", "nan",
    "None", "Null", "<NA>",
]

# --- Helper Functions ---

def load_data(filepath):
    """Loads the source CSV, forcing all columns to string type."""
    try:
        # Load all data as string to preserve leading zeros / lack thereof
        return pd.read_csv(filepath, dtype=str, keep_default_na=False)
    except FileNotFoundError:
        logging.error(f"Error: Source file not found at {filepath}")
        return None

def find_special_value(df, cols, value):
    """Finds the first row where the special value exists in any of the specified columns."""
    mask = (df[cols] == value).any(axis=1)
    return df[mask].head(1)

def find_missing_leading_zero(df, cols):
    """Finds the first row with a value that is numeric, unpadded, and not '0'."""
    
    def is_unpadded(s):
        """Check if a string is numeric and needs padding."""
        if not isinstance(s, str):
            return False
        # Is it a number?
        if s.isdigit():
            # Is it between 1 and 4 digits, and not just '0'?
            if 0 < len(s) < 5 and s != '0':
                return True
        return False

    # Apply the check across all label columns and find the first row
    mask = df[cols].applymap(is_unpadded).any(axis=1)
    return df[mask].head(1)

def find_unambiguous(df):
    """Finds the first row marked as Unambiguous."""
    # Check for various string versions of "true"
    true_values = ["True", "true", "TRUE", "1"]
    if "Unambiguous" not in df.columns:
        logging.warning("Warning: 'Unambiguous' column not found.")
        return pd.DataFrame(columns=df.columns)
        
    mask = df["Unambiguous"].isin(true_values)
    return df[mask].head(1)

def find_n_answers(df, cols, n):
    """Finds the first row with exactly 'n' non-empty answers."""
    # Replace all defined "empty" values with NaN
    temp_df = df[cols].replace(EMPTY_VALUES, np.nan)
    
    # Count how many are *not* NaN
    answer_counts = temp_df.notna().sum(axis=1)
    
    mask = (answer_counts == n)
    return df[mask].head(1)

def save_subset(df, filename):
    """Saves a dataframe to the output directory."""
    if df.empty:
        logging.warning(f"No data found for '{filename}'. CSV not created.")
        return
    
    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(filepath, index=False)
    logging.info(f"Successfully saved '{filename}'")

# --- Main Execution ---

def main():
    """Main function to run all filters and save subsets."""
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    df = load_data(SOURCE_FILE)
    if df is None:
        return

    logging.info(f"Loaded {len(df)} rows from {SOURCE_FILE}\n")
    logging.info("Starting filters...")

    # 1. '4+' item
    save_subset(
        find_special_value(df, CLERICAL_COLS, "4+"),
        "subset_1_clerical_four_plus.csv"
    )

    # 2. '-9' item
    save_subset(
        find_special_value(df, CLERICAL_COLS, "-9"),
        "subset_2_clerical_minus_nine.csv"
    )

    # 3. Missing leading zero
    save_subset(
        find_missing_leading_zero(df, ALL_LABEL_COLS),
        "subset_3_missing_leading_zero.csv"
    )

    # 4. Unambiguous item
    save_subset(
        find_unambiguous(df),
        "subset_4_unambiguous_true.csv"
    )

    # 5. Differing numbers of clerical answers
    save_subset(
        find_n_answers(df, CLERICAL_COLS, 1),
        "subset_5_clerical_1_answer.csv"
    )
    save_subset(
        find_n_answers(df, CLERICAL_COLS, 2),
        "subset_5_clerical_2_answers.csv"
    )
    save_subset(
        find_n_answers(df, CLERICAL_COLS, 3),
        "subset_5_clerical_3_answers.csv"
    )

    # 6. Differing numbers of model (LLM) answers
    save_subset(
        find_n_answers(df, MODEL_COLS, 1),
        "subset_6_model_1_answer.csv"
    )
    # Just picking a few numbers, you can change 3 and 5 to any count
    save_subset(
        find_n_answers(df, MODEL_COLS, 3),
        "subset_6_model_3_answers.csv"
