#!/usr/bin/env python3
"""
Quick test script to verify all modules load correctly
"""
import sys
import os

print("=" * 70)
print("🧪 DataNova - Module Validation Test")
print("=" * 70)
print()

# Test 1: Python Version
print("✓ Test 1: Python Version")
print(f"  Version: {sys.version}")
if sys.version_info < (3, 8):
    print("  ❌ Python 3.8+ required!")
    sys.exit(1)
print("  ✅ PASS\n")

# Test 2: Working Directory
print("✓ Test 2: Working Directory")
print(f"  Path: {os.getcwd()}")
print("  ✅ PASS\n")

# Test 3: Import database module
print("✓ Test 3: Database Module")
try:
    from database import DatabaseConnector
    print("  ✅ database.py loads successfully")
    print("  ✅ PASS\n")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    sys.exit(1)

# Test 4: Import setup_db module
print("✓ Test 4: Setup Database Module")
try:
    from setup_db import create_database, DB_PATH
    print(f"  ✅ setup_db.py loads successfully")
    print(f"  ✅ Database path: {DB_PATH}")
    print("  ✅ PASS\n")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    sys.exit(1)

# Test 5: Check .env file
print("✓ Test 5: Environment Configuration")
env_file = os.path.join(os.getcwd(), ".env")
if not os.path.exists(env_file):
    print(f"  ❌ .env file not found at {env_file}")
    sys.exit(1)

with open(env_file) as f:
    content = f.read()
    if "GROQ_API_KEY" in content:
        # Count characters (hide actual key)
        if "gsk_" in content:
            print(f"  ✅ GROQ_API_KEY configured")
            print("  ✅ PASS\n")
        else:
            print("  ⚠️  GROQ_API_KEY not set to a valid key")
    else:
        print("  ❌ GROQ_API_KEY not found in .env")
        sys.exit(1)

# Test 6: Import agent module
print("✓ Test 6: Agent Module")
try:
    from agent import run_generation, run_execution
    print("  ✅ agent.py loads successfully")
    print("  ✅ PASS\n")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    sys.exit(1)

# Test 7: Check database exists
print("✓ Test 7: Database File")
if os.path.exists(DB_PATH):
    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"  ✅ Database exists: {DB_PATH}")
    print(f"  ✅ Size: {size_mb:.2f} MB")
else:
    print(f"  ℹ️  Database not found (will be created on first run)")
    print(f"  ℹ️  Path: {DB_PATH}")
print("  ✅ PASS\n")

# Test 8: Dependencies check
print("✓ Test 8: Required Dependencies")
dependencies = {
    'streamlit': 'streamlit',
    'pandas': 'pandas',
    'plotly': 'plotly',
    'sqlalchemy': 'sqlalchemy',
    'groq': 'groq',
    'langgraph': 'langgraph',
}

missing = []
for name, module in dependencies.items():
    try:
        __import__(module)
        print(f"  ✅ {name}")
    except ImportError:
        print(f"  ❌ {name} - MISSING")
        missing.append(name)

if missing:
    print(f"\n  ⚠️  Missing: {', '.join(missing)}")
    print("  Run: pip install -r requirements.txt")
    sys.exit(1)

print("  ✅ PASS\n")

# Test 9: Port availability
print("✓ Test 9: Port Availability")
try:
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 8501))
    sock.close()
    if result == 0:
        print("  ⚠️  Port 8501 already in use (might be running)")
    else:
        print("  ✅ Port 8501 available")
    print("  ✅ PASS\n")
except Exception as e:
    print(f"  ⚠️  Could not check: {e}")

print("=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print()
print("🚀 Ready to run:")
print("   python run.py")
print("   or: run.bat (Windows)")
print("   or: streamlit run app.py")
print()
print("Opens at: http://localhost:8501")
print()
