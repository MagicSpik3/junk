# %% [markdown]
# # Data Pipeline Comparison: Legacy vs. New (Refactored)
#
# **Goal:** Compare the "Legacy" pipeline results against the "New" (Mark/160) pipeline results.
# **Fixes:** Added deterministic sorting to set-conversions and modularized execution.

# %%
import os
import dotenv
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Iterable, Set
from google.cloud import storage

# Custom Utils
from survey_assist_utils.configs.column_config import ColumnConfig
from survey_assist_utils.processing.flag_generator import FlagGenerator
from survey_assist_utils.data_cleaning.prep_data import prep_clerical_codes, prep_model_codes
from survey_assist_utils.evaluation.coder_alignment import LabelAccuracy
from survey_assist_utils.evaluation.mark_metrics import calc_simple_metrics
from survey_assist_utils.processing.pre_process_main_data import (
    expand_sic_candidates,
    add_initial_as_priority,
    add_likelihood_columns,
    expand_clerical_codes
)

# %%
# --- CONFIGURATION ---
dotenv.load_dotenv("../.env")
BUCKET_PREFIX = os.getenv("BUCKET_PREFIX", "")  # Fallback if env var missing
BUCKET_NAME = "survey_assist_sandbox_data"
DIGITS = 5

# Input Paths
PROMPT2_FILE = f"{BUCKET_PREFIX}two_prompt_pipeline/2025_09_full_2k_gemini25/STG5.parquet"
CLERICAL_IT2_FILE = f"{BUCKET_PREFIX}original_datasets/DSC_Rep_Sample_IT2.csv"
CLERICAL_IT2_4PLUS_FILE = f"{BUCKET_PREFIX}original_datasets/Codes_for_4_plus_DSC_Rep_Sample_IT2.csv"

# Output Paths
OUTPUT_CSV = 'pipeline_comparison_results.csv'
INVALID_CODES_CSV = 'invalid_codes.csv'
RESULTS_SUMMARY_CSV = 'results_summary.csv'

# Debug / Subsetting (Set USE_SUBSET to True to test on small data)
USE_SUBSET = False
SUBSET_UIDS = [] 

# %%
# --- HELPER FUNCTIONS ---

def subset_data(df: pd.DataFrame, uid_list: List[str]) -> pd.DataFrame:
    """Filters dataframe to specific UIDs if global subsetting is enabled."""
    if USE_SUBSET and uid_list:
        return df[df['unique_id'].isin(uid_list)].copy()
    return df

def flatten_to_sorted_list(data_structure: Iterable) -> List[Any]:
    """
    Recursively flattens a list of lists/sets and returns a SORTED list.
    CRITICAL for determinism.
    """
    flat_item = []
    for item in data_structure:
        if isinstance(item, (list, set, tuple)):
            flat_item.extend(item)
        else:
            flat_item.append(item)
    # Sort the final list to ensure determinism across runs
    try:
        return sorted(list(set(flat_item)))
    except TypeError:
        # Fallback if items are mixed types that can't be compared
        return list(flat_item)

def add_result_columns(df: pd.DataFrame, prefixes: Iterable[str], 
                      items_pattern: str = "{p} Items",
                      considered_pattern: str = "{p} Considered",
                      result_pattern: str = "{p} Result") -> pd.DataFrame:
    """Adds 'Result' columns based on Items/Considered boolean logic."""
    for p in prefixes:
        items_col = items_pattern.format(p=p)
        cons_col = considered_pattern.format(p=p)
        result_col = result_pattern.format(p=p)

        if items_col not in df.columns or cons_col not in df.columns:
            continue

        # Default to False for logic
        items = df[items_col].fillna(False).astype(bool)
        considered = df[cons_col].fillna(False).astype(bool)

        df[result_col] = np.where(considered, items, "")
    return df

# %%
# --- 1. DATA LOADING ---
print("Loading data...")
prompt2_df = pd.read_parquet(PROMPT2_FILE)
cc_it2_df = pd.read_csv(CLERICAL_IT2_FILE)
cc_it2_4plus_df = pd.read_csv(CLERICAL_IT2_4PLUS_FILE)

# Apply Subset if configured
prompt2_df = subset_data(prompt2_df, SUBSET_UIDS)
cc_it2_df = subset_data(cc_it2_df, SUBSET_UIDS)
cc_it2_4plus_df = subset_data(cc_it2_4plus_df, SUBSET_UIDS)

# %%
# --- 2. DATA PREPARATION ---
print("Preparing codes...")

# Prep Clerical
clerical_codes_it2 = prep_clerical_codes(cc_it2_df, cc_it2_4plus_df, digits=DIGITS)

# Export Invalid Codes (Side Effect)
invalids = clerical_codes_it2[clerical_codes_it2['clerical_codes_invalid'].apply(lambda x: len(x) > 0)]
if not invalids.empty:
    invalids[['unique_id']].to_csv(INVALID_CODES_CSV)

# Prep Model
model_prompt2 = prep_model_codes(prompt2_df, digits=DIGITS, out_col="sa_initial_codes")

# Merge Main Sets
merged = pd.merge(
    clerical_codes_it2[["unique_id", "clerical_codes"]],
    model_prompt2[["unique_id", "sa_initial_codes"]],
    on="unique_id",
    how="inner"
)

# %%
# --- 3. LEGACY PIPELINE METRICS ---
print("Running Legacy Metrics...")

eval_metrics = {}
# Calculate metrics
eval_metrics[(DIGITS, "m_2p")] = calc_simple_metrics(merged)

# Build DataFrame from metrics dictionary
plot_data = []
# Sort items to ensure iteration order is deterministic
for k, v in sorted(eval_metrics.items()):
    metrics_obj = v[0]
    raw_lists_1 = v[1]
    raw_lists_2 = v[2]
    
    plot_data.append({
        "digits": k[0],
        "method": k[1],
        "codability": metrics_obj.codability_metrics.initial_codable_prop,
        "f1": metrics_obj.ambiguity_metrics.f1,
        
        # Helper to flatten and SORT sets for determinism
        "OO Items": flatten_to_sorted_list(raw_lists_1.get("OO", [])),
        "OM Items": flatten_to_sorted_list(raw_lists_1.get("OM", [])),
        "MO Items": flatten_to_sorted_list(raw_lists_1.get("MO", [])),
        "MM Items": flatten_to_sorted_list(raw_lists_1.get("MM", [])),
        
        "OO Considered": flatten_to_sorted_list(raw_lists_2.get("OO", [])),
        "OM Considered": flatten_to_sorted_list(raw_lists_2.get("OM", [])),
        "MO Considered": flatten_to_sorted_list(raw_lists_2.get("MO", [])),
        "MM Considered": flatten_to_sorted_list(raw_lists_2.get("MM", []))
    })

plot_df_f1 = pd.DataFrame(plot_data)

# Map results back to Main DF
main_df = merged[['unique_id']].copy()
match_cols = ['OO', 'OM', 'MO', 'MM']

# Extract the list of UIDs for this specific digit/method combo
current_metrics = plot_df_f1.loc[(plot_df_f1['digits'] == DIGITS) & (plot_df_f1['method'] == 'm_2p')].iloc[0]

for col in match_cols:
    # Use set for fast lookup, but the source was sorted above
    true_uids = set(current_metrics[f"{col} Items"])
    cons_uids = set(current_metrics[f"{col} Considered"])
    
    main_df[f"{col} Items"] = main_df['unique_id'].isin(true_uids)
    main_df[f"{col} Considered"] = main_df['unique_id'].isin(cons_uids)

main_df = add_result_columns(main_df, match_cols)

# %%
# --- 4. NEW PIPELINE (MARK/160) ---
print("Running New Pipeline (Mark/160)...")

clerical_expanded = expand_clerical_codes(clerical_codes_it2)
prompt2_expanded = expand_sic_candidates(prompt2_df)
prompt2_expanded = add_initial_as_priority(prompt2_expanded)
prompt2_expanded, MAX_SIC_CODE = add_likelihood_columns(prompt2_expanded)

combined_mark = prompt2_expanded.merge(clerical_expanded, on="unique_id", how="inner")
flag_gen = FlagGenerator()
combined_mark = flag_gen.add_flags(combined_mark)

# Define Configs
configs = {
    "config_MM": ColumnConfig(
        model_label_cols=[f"sic_code_{i}" for i in range(1, MAX_SIC_CODE)],
        model_score_cols=[f"likelihood_{i}" for i in range(1, MAX_SIC_CODE)],
        clerical_label_cols=[f"clerical_code_{i}" for i in range(1, 8)],
        id_col="unique_id", filter_unambiguous=False
    ),
    "config_OM": ColumnConfig(
        model_label_cols=[f"sic_code_{i}" for i in range(1, MAX_SIC_CODE)],
        model_score_cols=[f"likelihood_{i}" for i in range(1, MAX_SIC_CODE)],
        clerical_label_cols=[f"clerical_code_{i}" for i in range(1, 2)],
        id_col="unique_id", filter_unambiguous=True
    ),
    "config_MO": ColumnConfig(
        model_label_cols=[f"sic_code_{i}" for i in range(1, 2)],
        model_score_cols=[f"likelihood_{i}" for i in range(1, 2)],
        clerical_label_cols=[f"clerical_code_{i}" for i in range(1, 8)],
        id_col="unique_id", filter_unambiguous=False
    ),
    "config_OO": ColumnConfig(
        model_label_cols=[f"sic_code_{i}" for i in range(1, 2)],
        model_score_cols=[f"likelihood_{i}" for i in range(1, 2)],
        clerical_label_cols=[f"clerical_code_{i}" for i in range(1, 2)],
        id_col="unique_id", filter_unambiguous=True
    )
}

# Run Tests
mark_results = []
for name, config in configs.items():
    analyzer = LabelAccuracy(df=combined_mark, column_config=config)
    df_res = analyzer.df
    mask_true = df_res['is_correct'].astype(bool)
    
    # Store UIDs
    mark_results.append({
        "variable_name": name,
        "uid_list_true": set(df_res.loc[mask_true, 'unique_id']),
        "uid_list_false": set(df_res.loc[~mask_true, 'unique_id']),
        # Assuming metrics are needed for "Considered" logic (union of true/false usually)
        "uid_list_metrics": set(df_res['unique_id']) 
    })

# Map Mark results back to a clean dataframe
main_df_mark = merged[['unique_id']].copy()

for res in mark_results:
    cfg = res["variable_name"]
    uids = main_df_mark["unique_id"]
    
    # Deterministic checks using sets
    main_df_mark[f"{cfg}_True"] = uids.isin(res["uid_list_true"])
    main_df_mark[f"{cfg}_False"] = uids.isin(res["uid_list_false"])
    # If a UID is in either true or false list, it was "Considered"
    main_df_mark[f"{cfg}_Considered"] = uids.isin(res["uid_list_true"] | res["uid_list_false"])

main_df_mark = add_result_columns(
    main_df_mark, 
    prefixes=['OO', 'OM', 'MO', 'MM'],
    items_pattern="config_{p}_True",
    considered_pattern="config_{p}_Considered",
    result_pattern="config_{p}_Result"
)

# %%
# --- 5. MERGE & DIAGNOSTICS ---
print("Merging and generating diagnostics...")

final_df = main_df.merge(main_df_mark, on='unique_id')

# Add Diagnostic Flags
# 1. Invalid Codes
ids_with_invalid = set(clerical_codes_it2.loc[clerical_codes_it2["clerical_codes_invalid"].map(len) > 0, "unique_id"])
final_df["has_invalid"] = final_df["unique_id"].isin(ids_with_invalid)

# 2. Too many codes (CC)
ids_many_cc = set(clerical_codes_it2.loc[clerical_codes_it2["clerical_codes"].map(len) > 7, "unique_id"])
final_df["has_many_cc"] = final_df["unique_id"].isin(ids_many_cc)

# 3. Too many codes (LLM)
ids_many_llm = set(model_prompt2.loc[model_prompt2["sa_initial_codes"].map(len) > 7, "unique_id"])
final_df["has_many_llm"] = final_df["unique_id"].isin(ids_many_llm)

# Select columns for export
export_cols = ['unique_id', 'OO Result', 'OM Result', 'MO Result', 'MM Result', 
               'config_OO_Result', 'config_OM_Result', 'config_MO_Result', 'config_MM_Result',
               'has_invalid', 'has_many_cc', 'has_many_llm']

print(f"Exporting to {OUTPUT_CSV}...")
final_df[export_cols].to_csv(OUTPUT_CSV, index=False)

# %%
# --- 6. SUMMARY STATS (Optional) ---
# Calculate differences between the two pipelines
summary_rows = []
prefixes = ['OO', 'OM', 'MO', 'MM']

def normalize_result(s):
    """Normalizes result columns to boolean or empty string."""
    return s.replace({np.nan: ""}).map(lambda x: True if str(x) == "True" else (False if str(x) == "False" else ""))

for p in prefixes:
    legacy_col = normalize_result(final_df[f"{p} Result"])
    config_col = normalize_result(final_df[f"config_{p}_Result"])
    
    # Count discrepancies
    # Legacy says True, Config says NOT True (False or Empty)
    legacy_true_config_not = ((legacy_col == True) & (config_col != True)).sum()
    
    # Config says True, Legacy says NOT True
    config_true_legacy_not = ((config_col == True) & (legacy_col != True)).sum()

    summary_rows.append({
        "Type": p,
        "Legacy_True_Config_Mismatch": legacy_true_config_not,
        "Config_True_Legacy_Mismatch": config_true_legacy_not
    })

pd.DataFrame(summary_rows).to_csv(RESULTS_SUMMARY_CSV, index=False)
print("Done.")
