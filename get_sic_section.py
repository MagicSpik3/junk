def get_sic_section(sic_code_str):
    """
    Returns the SIC 2007 Section letter for a 5-digit SIC code.
    """
    try:
        # Extract the first two digits (the Division)
        division = int(sic_code_str[0:2])
    except (ValueError, TypeError, IndexError):
        return None  # Invalid input

    if 1 <= division <= 3:
        return 'A'
    elif 5 <= division <= 9:
        return 'B'
    elif 10 <= division <= 33:
        return 'C'
    elif division == 35:
        return 'D'
    elif 36 <= division <= 39:
        return 'E'
    elif 41 <= division <= 43:
        return 'F'
    elif 45 <= division <= 47:
        return 'G'
    elif 49 <= division <= 53:
        return 'H'
    elif 55 <= division <= 56:
        return 'I'
    elif 58 <= division <= 63:
        return 'J'
    elif 64 <= division <= 66:
        return 'K'
    elif division == 68:
        return 'L'
    elif 69 <= division <= 75:
        return 'M'
    elif 77 <= division <= 82:
        return 'N'
    elif division == 84:
        return 'O'
    elif division == 85:
        return 'P'
    elif 86 <= division <= 88:
        return 'Q'
    elif 90 <= division <= 93:
        return 'R'
    elif 94 <= division <= 96:
        return 'S'
    elif 97 <= division <= 98:
        return 'T'
    elif division == 99:
        return 'U'
    else:
        # Covers unused divisions (e.g., 00, 04, 34, 40, etc.)
        return None 

# --- Examples ---
print(f"99000 -> {get_sic_section('99000')}") # Output: 99000 -> U
print(f"03220 -> {get_sic_section('03220')}") # Output: 03220 -> A
print(f"45112 -> {get_sic_section('45112')}") # Output: 45112 -> G
print(f"68209 -> {get_sic_section('68209')}") # Output: 68209 -> L
