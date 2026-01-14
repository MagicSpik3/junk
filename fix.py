def expand_clerical_codes(df, max_cols=7):
    # ... inside the function logic ...
    
    def expand_row(row_set):
        # THE FIX: Sort the list before slicing!
        # This ensures 'A' always comes before 'B', and 'Z' is always the one dropped
        sorted_codes = sorted(list(row_set))
        
        # Pad with None if fewer than max_cols
        padded = sorted_codes + [None] * (max_cols - len(sorted_codes))
        
        # Truncate if more than max_cols (Deterministic data loss is better than random)
        return padded[:max_cols]

    # Apply this logic to create the columns
    # ...
