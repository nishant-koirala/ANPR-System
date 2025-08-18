import re
from config.license_formats import (
    validate_license_format, 
    format_license_plate, 
    clean_text_for_format
)

def flatten_text(obj):
    """Handle EasyOCR text in various formats (string, list, nested list)"""
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, list):
        result = []
        for item in obj:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, list):
                result.extend(flatten_text(item))
        return ' '.join(result)
    else:
        return str(obj)

def clean_ocr_text(text):
    """Clean common OCR errors"""
    cleaned = re.sub(r'[^A-Z0-9]', '', text)
    
    replacements = {
        '0': 'O', '1': 'I', '5': 'S', '6': 'G', '8': 'B',
        'Q': 'O', 'Z': '2', '@': 'A'
    }
    
    result = ''
    for i, char in enumerate(cleaned):
        if char in replacements:
            if i < 2 or i >= len(cleaned) - 2:  # Likely letter positions
                if char in '01568':
                    result += replacements[char]
                else:
                    result += char
            else:  # Middle positions, likely numbers
                if char in 'OISZGB':
                    reverse_map = {'O': '0', 'I': '1', 'S': '5', 'Z': '2', 'G': '6', 'B': '8'}
                    result += reverse_map.get(char, char)
                else:
                    result += char
        else:
            result += char
    
    return result
