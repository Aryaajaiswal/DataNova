#!/usr/bin/env python3
"""
DataNova Launcher
Quick startup script for the Text-to-SQL agent
"""

import subprocess
import sys
import os
from pathlib import Path

def check_env():
    """Verify .env file exists"""
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env file not found!")
        print("\nCreating .env template...")
        with open(".env", "w") as f:
            f.write("GROQ_API_KEY=your_groq_api_key_here\n")
        print("✓ .env created. Please add your GROQ_API_KEY and run again.")
        return False
    
    with open(".env") as f:
        content = f.read()
        if "your_groq_api_key_here" in content or not content.strip():
            print("⚠️  GROQ_API_KEY not configured in .env")
            return False
    
    return True

def main():
    print("\n" + "="*50)
    print("⚡ DataNova - Text-to-SQL Data Agent")
    print("="*50 + "\n")
    
    # Check environment
    if not check_env():
        print("\n❌ Please configure your GROQ_API_KEY in .env")
        sys.exit(1)
    
    print("✓ Environment configured\n")
    print("🚀 Starting Streamlit app...\n")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--logger.level=warning"
        ], check=True)
    except KeyboardInterrupt:
        print("\n\n👋 DataNova stopped.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
