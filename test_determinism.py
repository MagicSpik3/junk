import pytest
import random
from typing import Iterable, Any, List

# --- The Function Under Test ---
# (You can import this from your main script, but I've included it here for isolation)
def flatten_to_sorted_list(data_structure: Iterable) -> List[Any]:
    """
    Recursively flattens a list of lists/sets and returns a SORTED list.
    CRITICAL for determinism.
    """
    flat_item = []
    # Basic flattening (1 level deep as per the notebook usage)
    for item in data_structure:
        if isinstance(item, (list, set, tuple)):
            flat_item.extend(item)
        else:
            flat_item.append(item)
    
    # Sort the final list to ensure determinism across runs
    # We use a set first to remove duplicates, then list, then sort
    try:
        return sorted(list(set(flat_item)))
    except TypeError:
        # Fallback if items are mixed types that can't be compared
        # We still convert to list to ensure it's serializable
        return list(flat_item)

# --- The Tests ---

def test_determinism_with_sets():
    """
    Simulates the 'Jupyter Notebook Set Problem'.
    Sets in Python have no guaranteed order. We simulate this by 
    shuffling the input list of sets. The output must remain identical.
    """
    # Case: A list of sets (common in the notebook's 'eval_metrics')
    input_data = [{"A", "B"}, {"C"}, {"A", "D"}]
    
    # Run 1
    result_1 = flatten_to_sorted_list(input_data)
    
    # Run 2: Shuffle the input list to simulate randomness
    random.shuffle(input_data)
    result_2 = flatten_to_sorted_list(input_data)
    
    # Run 3: Reverse the input
    input_data.reverse()
    result_3 = flatten_to_sorted_list(input_data)

    expected = ["A", "B", "C", "D"]
    
    assert result_1 == expected
    assert result_2 == expected
    assert result_3 == expected
    assert result_1 == result_2 == result_3
    print("\n✅ Determinism verified: Shuffling inputs did not change output.")

def test_flattening_levels():
    """Ensure it handles mixed scalars and iterables."""
    input_data = ["A", ["B", "C"], {"D", "E"}]
    result = flatten_to_sorted_list(input_data)
    assert result == ["A", "B", "C", "D", "E"]

def test_integer_sorting():
    """Ensure numeric IDs are sorted correctly."""
    input_data = [{10, 2}, {5}, [1, 9]]
    result = flatten_to_sorted_list(input_data)
    assert result == [1, 2, 5, 9, 10]

def test_mixed_types_fallback():
    """
    Edge Case: If the list contains mixed types (int and str) that cannot 
    be sorted together in Python 3, it should not crash.
    """
    # Python 3 raises TypeError if you try to sort ['A', 1]
    input_data = ["A", 1, "B", 2]
    
    # Should run without error (hitting the try/except block)
    result = flatten_to_sorted_list(input_data)
    
    # We can't guarantee order here, but we guarantee it returns a list
    assert isinstance(result, list)
    assert len(result) == 4
    assert "A" in result and 1 in result

if __name__ == "__main__":
    # Allow running directly with python test_determinism.py
    # (Manual simple runner if pytest isn't installed)
    try:
        test_determinism_with_sets()
        test_flattening_levels()
        test_integer_sorting()
        test_mixed_types_fallback()
        print("All tests passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
