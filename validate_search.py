#!/usr/bin/env python3
"""
Test SearchPlatePage import and creation
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_search_plate_page():
    """Test SearchPlatePage creation"""
    try:
        print("Testing SearchPlatePage import...")
        from src.ui.search_plate_page import SearchPlatePage
        print("✅ SearchPlatePage imported successfully")
        
        print("Testing database connection...")
        from src.db import get_database
        db = get_database()
        print("✅ Database connected successfully")
        
        print("Testing SearchPlatePage creation...")
        page = SearchPlatePage(db.get_session)
        print("✅ SearchPlatePage created successfully")
        
        print("All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_search_plate_page()
