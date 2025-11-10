"""
Test script to verify stolen vehicle detection
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.db.database import get_database
from src.db.special_vehicles_db import SpecialVehiclesDB

print("=" * 60)
print("STOLEN VEHICLE DETECTION TEST")
print("=" * 60)

# Initialize database
db = get_database()
special_db = SpecialVehiclesDB(db.get_session)

# Test plate
test_plate = "१६च१०२०"

print(f"\n1. Testing plate: {test_plate}")

# Check if stolen
print(f"\n2. Checking if {test_plate} is stolen...")
stolen = special_db.check_if_stolen(test_plate)

if stolen:
    print(f"   ✅ FOUND IN STOLEN VEHICLES!")
    print(f"   - ID: {stolen.id}")
    print(f"   - Plate: {stolen.plate_number}")
    print(f"   - Owner: {stolen.owner_name}")
    print(f"   - Status: {stolen.status}")
    print(f"   - Dashboard Alert: {stolen.enable_dashboard_alert}")
else:
    print(f"   ❌ NOT FOUND in stolen vehicles")
    print(f"\n   Checking all stolen vehicles:")
    all_stolen = special_db.get_all_stolen_vehicles()
    if all_stolen:
        for sv in all_stolen:
            print(f"   - {sv.plate_number} (Status: {sv.status})")
    else:
        print(f"   No stolen vehicles in database!")

# Check alert cooldown
if stolen:
    print(f"\n3. Checking alert cooldown...")
    can_alert = special_db.check_alert_cooldown(stolen.id, cooldown_minutes=5)
    if can_alert:
        print(f"   ✅ Can send alert (cooldown passed)")
    else:
        print(f"   ⏳ Alert in cooldown period")

# Get alert config
print(f"\n4. Checking alert configuration...")
config = special_db.get_alert_config()
if config:
    print(f"   ✅ Alert config found")
    print(f"   - Dashboard alerts: {config.dashboard_alert_enabled}")
    print(f"   - Cooldown: {config.alert_cooldown_minutes} minutes")
else:
    print(f"   ❌ No alert configuration")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
