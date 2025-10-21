#!/usr/bin/env python3
"""
TwitterExplorer Modern Streamlit App Launcher
===========================================

Quick launcher for the comprehensive TwitterExplorer Streamlit interface.
This script performs pre-launch validation and starts the Streamlit app.

Usage:
    python launch_app.py
    
Or directly:
    streamlit run streamlit_app_modern.py
"""

import sys
import subprocess
import os
from pathlib import Path

def validate_environment():
    """Validate that all requirements are met"""
    print("Validating TwitterExplorer environment...")
    
    # Check if we're in the right directory
    current_dir = Path.cwd()
    expected_files = [
        'twitterexplorer/streamlit_app_modern.py',
        'twitterexplorer/investigation_engine.py', 
        'twitterexplorer/llm_model_manager.py',
        'twitterexplorer/.streamlit/secrets.toml',
        'twitterexplorer/config/models.yaml'
    ]
    
    for file_path in expected_files:
        if not (current_dir / file_path).exists():
            print(f"Missing required file: {file_path}")
            return False
    
    # Test imports by changing to twitterexplorer directory
    import sys
    sys.path.insert(0, str(current_dir / 'twitterexplorer'))
    
    try:
        import streamlit as st
        import toml
        import yaml
        from investigation_engine import InvestigationEngine
        from llm_model_manager import LLMModelManager
        print("All dependencies available")
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    
    # Test secrets loading
    try:
        with open('twitterexplorer/.streamlit/secrets.toml', 'r') as f:
            secrets = toml.load(f)
        
        required_keys = ['RAPIDAPI_KEY', 'OPENAI_API_KEY', 'GEMINI_API_KEY']
        missing_keys = [key for key in required_keys if key not in secrets]
        
        if missing_keys:
            print(f"Missing API keys: {missing_keys}")
            print("   App will still start but some features may not work")
        else:
            print("All API keys configured")
            
    except Exception as e:
        print(f"Secrets file issue: {e}")
        print("   App will start but API features may not work")
    
    print("Environment validation complete")
    return True

def launch_streamlit():
    """Launch the Streamlit app"""
    print("\nLaunching TwitterExplorer Advanced Investigation System...")
    print("   Opening in your default browser...")
    print("   Use Ctrl+C to stop the server")
    print("\n" + "="*50)
    
    # Change to twitterexplorer directory
    os.chdir('twitterexplorer')
    
    try:
        # Launch streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_app_modern.py"
        ], check=True)
    except KeyboardInterrupt:
        print("\n\nTwitterExplorer stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\nFailed to start Streamlit: {e}")
        print("\nTry running directly:")
        print("  cd twitterexplorer")
        print("  streamlit run streamlit_app_modern.py")

def main():
    """Main launcher function"""
    print("TwitterExplorer Advanced Investigation System")
    print("=" * 45)
    
    if not validate_environment():
        print("\nEnvironment validation failed")
        print("Please check the requirements and try again")
        sys.exit(1)
    
    print("\nApp Features Available:")
    print("  * Real-time model provider switching (OpenAI/Gemini)")
    print("  * Interactive D3.js graph visualization")
    print("  * Live progress updates during investigations")  
    print("  * Complete investigation pipeline with bridge integration")
    print("  * Session management with export functionality")
    print("  * Comprehensive reporting and analysis")
    
    launch_streamlit()

if __name__ == "__main__":
    main()