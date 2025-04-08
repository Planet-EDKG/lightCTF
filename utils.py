import re
from difflib import SequenceMatcher

def normalize_text(text: str) -> str:
    """Normalizes text for comparison by:
    - Converting to lowercase
    - Removing special characters
    - Converting spaces and hyphens to single spaces
    """
    # Convert to lowercase
    text = text.lower().strip()
    # Replace hyphens and underscores with spaces
    text = re.sub(r'[-_]', ' ', text)
    # Remove all other special characters
    text = re.sub(r'[^a-z0-9\s]', '', text)
    # Convert multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)
    return text

def validate_flag_format(submitted_flag: str, correct_flag: str) -> tuple[bool, str, float]:
    """
    Validates a submitted flag against the correct flag with flexible format matching
    
    Returns:
        tuple(is_correct, message, similarity_score)
    """
    # Direct match first
    if submitted_flag.strip().lower() == correct_flag.strip().lower():
        return True, "Correct flag!", 1.0
    
    # Normalize both flags
    submitted_normalized = normalize_text(submitted_flag)
    correct_normalized = normalize_text(correct_flag)
    
    # Check normalized equality
    if submitted_normalized == correct_normalized:
        return True, "Correct flag!", 1.0
    
    # Calculate similarity on normalized text
    similarity = SequenceMatcher(None, submitted_normalized, correct_normalized).ratio()
    
    # Common format checks
    format_checks = [
        (r'\s+', 'Remove extra spaces'),
        (r'[{}]', 'Remove curly braces'),
        (r'flag:', 'Remove "flag:" prefix'),
        (r'ctf{(.+)}', 'Use the format: FLAG{...}')
    ]
    
    for pattern, hint in format_checks:
        if re.search(pattern, submitted_flag):
            return False, f"Format error: {hint}", similarity
    
    if similarity > 0.9:
        return False, "Very close! Check your spelling.", similarity
    elif similarity > 0.7:
        return False, "You're on the right track!", similarity
    
    return False, "Incorrect flag.", similarity