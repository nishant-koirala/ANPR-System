# License plate format definitions for NEPALI ANPR system

import string

# Character mappings for OCR correction
CHAR_TO_INT = {'O': '0', 'I': '1', 'J': '3', 'A': '4', 'G': '6', 'S': '5'}
INT_TO_CHAR = {'0': 'O', '1': 'I', '3': 'J', '4': 'A', '6': 'G', '5': 'S'}

class LicenseFormat:
    """Base class for license plate formats"""
    
    def __init__(self, name, description, length, pattern):
        self.name = name
        self.description = description
        self.length = length
        self.pattern = pattern  # L=Letter, D=Digit
    
    def validate(self, text):
        """Validate if text matches this format"""
        raise NotImplementedError
    
    def format_text(self, text):
        """Format text according to this format"""
        raise NotImplementedError
    
    def clean_text(self, text):
        """Clean text for this format"""
        raise NotImplementedError

class Format1(LicenseFormat):
    """Format 1: AA00AAA (7 characters) - Traditional Nepali format"""
    
    def __init__(self):
        super().__init__(
            name="format1",
            description="AA00AAA (7 characters)",
            length=7,
            pattern="LLDDLLL"
        )
    
    def validate(self, text):
        """Validate Format 1: AA00AAA"""
        # Clean text first
        clean_text = text.replace(' ', '').replace('\n', '').upper()
        
        # Allow 4-7 characters for flexibility
        if len(clean_text) < 4 or len(clean_text) > 7:
            return False
        
        # If it's just 4 digits, accept it (partial plate)
        if len(clean_text) == 4 and clean_text.isdigit():
            return True
        
        # If it's not exactly 7 characters, reject for full format
        if len(clean_text) != 7:
            return False
        
        return (
            (clean_text[0] in string.ascii_uppercase or clean_text[0] in INT_TO_CHAR.keys()) and
            (clean_text[1] in string.ascii_uppercase or clean_text[1] in INT_TO_CHAR.keys()) and
            (clean_text[2] in '0123456789' or clean_text[2] in CHAR_TO_INT.keys()) and
            (clean_text[3] in '0123456789' or clean_text[3] in CHAR_TO_INT.keys()) and
            (clean_text[4] in string.ascii_uppercase or clean_text[4] in INT_TO_CHAR.keys()) and
            (clean_text[5] in string.ascii_uppercase or clean_text[5] in INT_TO_CHAR.keys()) and
            (clean_text[6] in string.ascii_uppercase or clean_text[6] in INT_TO_CHAR.keys())
        )
    
    def format_text(self, text):
        """Format text for Format 1"""
        # Handle 4-digit partial plates
        if len(text) == 4 and text.isdigit():
            return text  # Return as-is for partial plates
        
        if len(text) != 7:
            return text
            
        license_plate_ = ''
        # Position-based character mapping
        mapping = {
            0: INT_TO_CHAR,  # Letter
            1: INT_TO_CHAR,  # Letter
            2: CHAR_TO_INT,  # Digit
            3: CHAR_TO_INT,  # Digit
            4: INT_TO_CHAR,  # Letter
            5: INT_TO_CHAR,  # Letter
            6: INT_TO_CHAR   # Letter
        }
        
        for i, char in enumerate(text):
            if char in mapping[i]:
                license_plate_ += mapping[i][char]
            else:
                license_plate_ += char
        
        return license_plate_
    
    def clean_text(self, text):
        """Clean text for Format 1 - remove spaces"""
        return str(text).upper().replace(' ', '')

class Format2(LicenseFormat):
    """Format 2: AA 1111 - New Nepali format (exactly 4 digits)"""
    
    def __init__(self):
        super().__init__(
            name="format2",
            description="AA 1111",
            length=6,  # Exactly 6 characters (2 letters + 4 digits)
            pattern="LLDDDD"
        )
    
    def validate(self, text):
        """Validate Format 2: AA 1111 (exactly 2 letters + 4 digits)"""
        # Remove spaces and newlines for validation
        clean_text = text.replace(' ', '').replace('\n', '').upper()
        
        # Allow 4-6 characters for flexibility
        if len(clean_text) < 4 or len(clean_text) > 6:
            return False
        
        # If it's just 4 digits, accept it (partial plate)
        if len(clean_text) == 4 and clean_text.isdigit():
            return True
        
        # Must be exactly 6 characters (AA + 1111)
        if len(clean_text) != 6:
            return False
        
        # First 2 must be letters (allow common OCR substitutions)
        for i in range(2):
            if not (clean_text[i] in string.ascii_uppercase or clean_text[i] in INT_TO_CHAR.keys()):
                return False
        
        # Last 4 must be digits (allow common OCR substitutions)
        for i in range(2, 6):
            if not (clean_text[i] in '0123456789' or clean_text[i] in CHAR_TO_INT.keys()):
                return False
        
        return True
    
    def format_text(self, text):
        """Format text for Format 2"""
        # Clean and validate
        clean_text = text.replace(' ', '').replace('\n', '')
        
        # Handle 4-digit partial plates
        if len(clean_text) == 4 and clean_text.isdigit():
            return clean_text  # Return as-is for partial plates
        
        if len(clean_text) != 6:
            return text
        
        license_plate_ = ''
        # Apply character mapping for each position
        for i, char in enumerate(clean_text):
            if i < 2:  # Letters
                if char in INT_TO_CHAR:
                    license_plate_ += INT_TO_CHAR[char]
                else:
                    license_plate_ += char
            else:  # Digits
                if char in CHAR_TO_INT:
                    license_plate_ += CHAR_TO_INT[char]
                else:
                    license_plate_ += char
        
        # Format as AA 1111
        return f"{license_plate_[:2]} {license_plate_[2:]}"
    
    def clean_text(self, text):
        """Clean text for Format 2 - keep spaces and newlines"""
        return str(text).upper()

# Format registry
LICENSE_FORMATS = {
    'format1': Format1(),
    'format2': Format2()
}

def get_format(format_name):
    """Get format instance by name"""
    return LICENSE_FORMATS.get(format_name)

def get_all_formats():
    """Get all available formats"""
    return LICENSE_FORMATS

def validate_license_format(text, format_name):
    """Validate text against specific format"""
    format_obj = get_format(format_name)
    if format_obj:
        return format_obj.validate(text)
    return False

def format_license_plate(text, format_name):
    """Format text according to specific format"""
    format_obj = get_format(format_name)
    if format_obj:
        return format_obj.format_text(text)
    return text

def clean_text_for_format(text, format_name):
    """Clean text for specific format"""
    format_obj = get_format(format_name)
    if format_obj:
        return format_obj.clean_text(text)
    return str(text).upper()

# Format display names for UI
FORMAT_DISPLAY_NAMES = {
    'format1': "Format 1: AA00AAA (7 characters)",
    'format2': "Format 2: AA 1111 (6 characters)",
    'auto': "Automatic: Try both formats"
}
