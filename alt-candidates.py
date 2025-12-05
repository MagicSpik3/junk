def extract_alt_candidates_n_digit_codes(
    alt_candidates: list[dict],
    code_name: str,
    n: int = EXPECTED_CODE_LENGTH,
    score_name: str = "likelihood",
    threshold: float = 0,
) -> tuple[set[str], set[str]]:  # <--- Return type changed
    """Extracts alternative sic codes...
    
    Returns:
        tuple[set[str], set[str]]:
            - cleaned_set: Set of valid, pruned SIC codes.
            - invalid_set: Set of raw codes that were invalid.
    """
    # Handle the edge case where input is just a string (consistency check)
    if isinstance(alt_candidates, str):
        return get_clean_n_digit_codes(parse_numerical_code(alt_candidates), n)

    if not isinstance(alt_candidates, Iterable):
        logger.warning(
            "Expected a list of dicts for alt_candidates, got %s", type(alt_candidates)
        )
        return set(), set() # Return empty tuple

    cleaned: dict[str, float] = {}
    invalid_set: set[str] = set() # <--- New accumulator

    for item in alt_candidates:
        raw_code = f"{item.get(code_name, '')}"
        
        # Use the low-level helper
        codes = get_clean_n_digit_one_code(raw_code, n)
        
        # LOGIC CHANGE: If no codes returned, track as invalid
        if not codes:
            # You might want to skip logging here if it's too noisy, 
            # or keep it consistent.
            invalid_set.add(raw_code)
            continue

        score = item.get(score_name, 0)
        for code in codes:
            if code in cleaned:
                cleaned[code] = max(cleaned[code], score)
            else:
                cleaned[code] = score

    # Pruning Logic (remains the same)
    pruned = {code for code, score in cleaned.items() if score >= threshold}
    
    # If pruning reduced it to 1, return that. Otherwise return all found.
    final_valid = pruned if len(pruned) == 1 else set(cleaned)

    return final_valid, invalid_set



prep_model_codes


# Inside prep_model_codes...
    if alt_codes_col is not None:
        # ... logic to find missing rows ...
        
        # OLD:
        # alternatives = input_df.loc[miss_msk, alt_codes_col].apply(...)
        # out_df.loc[miss_msk, out_col] = alternatives

        # NEW:
        # Run the extraction
        alt_results = input_df.loc[miss_msk, alt_codes_col].apply(
            extract_alt_candidates_n_digit_codes,
            code_name=alt_codes_name,
            n=digits,
            threshold=threshold,
        )
        
        # Unpack the tuple result into two columns
        # Note: apply on multiple rows usually returns a Series of tuples
        # You might need to split them or use the lambda x: pd.Series(x) trick
        
        # Cleaner way using your lambda pattern:
        expanded_results = input_df.loc[miss_msk, alt_codes_col].apply(
             lambda x: pd.Series(
                 extract_alt_candidates_n_digit_codes(
                     x, code_name=alt_codes_name, n=digits, threshold=threshold
                 )
             )
        )
        
        out_df.loc[miss_msk, out_col] = expanded_results[0]
        
        # Decide: Do you want to merge these invalid codes into the existing invalid column?
        # If so:
        # out_df.loc[miss_msk, "invalid_codes"] = out_df.loc[miss_msk, "invalid_codes"] | expanded_results[1]

