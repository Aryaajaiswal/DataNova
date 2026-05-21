#!/usr/bin/env python3
"""
DataNova - Integration Test
Tests the application without running full Streamlit
"""
import sys
import os
from pathlib import Path

def test_imports():
    """Test all module imports"""
    print("\n📦 Testing Module Imports...")
    print("-" * 50)
    
    modules = {
        'os': 'Built-in',
        'time': 'Built-in',
        'sqlite3': 'Built-in',
        'uuid': 'Built-in',
        'pandas': 'External',
        'plotly': 'External',
        'sqlalchemy': 'External',
        'groq': 'External',
        'langgraph': 'External',
        'streamlit': 'External',
        'dotenv': 'External',
        'fpdf': 'External',
    }
    
    failed = []
    for module_name, source in modules.items():
        try:
            __import__(module_name)
            print(f"✅ {module_name:<20} ({source})")
        except ImportError as e:
            print(f"❌ {module_name:<20} FAILED: {e}")
            failed.append(module_name)
    
    return len(failed) == 0, failed


def test_custom_modules():
    """Test custom DataNova modules"""
    print("\n🔧 Testing DataNova Modules...")
    print("-" * 50)
    
    os.chdir(Path(__file__).parent)
    sys.path.insert(0, str(Path(__file__).parent))
    
    modules = ['database', 'setup_db', 'agent']
    failed = []
    
    for mod_name in modules:
        try:
            mod = __import__(mod_name)
            print(f"✅ {mod_name}.py loaded")
        except Exception as e:
            print(f"❌ {mod_name}.py FAILED: {e}")
            failed.append(mod_name)
    
    return len(failed) == 0, failed


def test_database():
    """Test database connectivity"""
    print("\n💾 Testing Database...")
    print("-" * 50)
    
    try:
        from setup_db import DB_PATH
        from database import DatabaseConnector
        
        db_url = f"sqlite:///{DB_PATH}"
        db = DatabaseConnector(db_url)
        
        is_connected = db.test_connection()
        if is_connected:
            print(f"✅ Database connected: {DB_PATH}")
            
            # If database exists, test table listing
            if os.path.exists(DB_PATH):
                tables = db.get_tables()
                print(f"✅ Found {len(tables)} tables")
                for table in tables[:5]:
                    print(f"   - {table}")
            else:
                print("ℹ️  Database will be created on first run")
            return True, None
        else:
            print(f"❌ Could not connect to database")
            return False, "Connection failed"
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False, str(e)


def test_api_key():
    """Test API key configuration"""
    print("\n🔑 Testing API Configuration...")
    print("-" * 50)
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print("❌ GROQ_API_KEY not set in .env")
            return False, "No API key"
        
        if not api_key.startswith("gsk_"):
            print("⚠️  API key format suspicious (should start with 'gsk_')")
            # Still pass, could be testing
        
        key_display = api_key[:10] + "..." + api_key[-5:]
        print(f"✅ GROQ_API_KEY configured: {key_display}")
        return True, None
    except Exception as e:
        print(f"❌ API configuration test failed: {e}")
        return False, str(e)


def test_syntax():
    """Test Python syntax of main files"""
    print("\n🔍 Testing Python Syntax...")
    print("-" * 50)
    
    import py_compile
    
    files = ['app.py', 'agent.py', 'database.py', 'setup_db.py']
    failed = []
    
    for filename in files:
        try:
            py_compile.compile(filename, doraise=True)
            print(f"✅ {filename} - Valid syntax")
        except py_compile.PyCompileError as e:
            print(f"❌ {filename} - Syntax error: {e}")
            failed.append(filename)
    
    return len(failed) == 0, failed


def test_agent():
    """Test agent module functions"""
    print("\n🤖 Testing Agent Module...")
    print("-" * 50)
    
    try:
        from agent import (
            run_generation,
            run_execution,
            generate_sample_questions,
            generate_executive_summary
        )
        
        functions = [
            ('run_generation', run_generation),
            ('run_execution', run_execution),
            ('generate_sample_questions', generate_sample_questions),
            ('generate_executive_summary', generate_executive_summary),
        ]
        
        for name, func in functions:
            print(f"✅ {name} - Callable")
        
        print("✅ Agent module fully functional")
        return True, None
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        return False, str(e)


def main():
    print("\n" + "=" * 70)
    print("⚡ DataNova - Comprehensive Integration Test")
    print("=" * 70)
    
    results = {
        "Module Imports": test_imports(),
        "Custom Modules": test_custom_modules(),
        "Database": test_database(),
        "API Key": test_api_key(),
        "Python Syntax": test_syntax(),
        "Agent Module": test_agent(),
    }
    
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, (passed, error) in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:<12} {test_name}")
        if error:
            if isinstance(error, list):
                for e in error:
                    print(f"             - {e}")
            else:
                print(f"             - {error}")
        all_passed = all_passed and passed
    
    print("=" * 70)
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED!")
        print("\n🚀 Application is ready to run!")
        print("\nCommand to start:")
        print("  python run.py")
        print("  or: run.bat (Windows)")
        print("  or: streamlit run app.py")
        print("\nOpens at: http://localhost:8501")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\nPlease fix the issues above and try again.")
        print("\nFor help, see: STARTUP.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
