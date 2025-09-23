#!/usr/bin/env python3
"""
HAZOP Analysis Application Launcher
This script sets up and launches the complete HAZOP analysis platform.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required.")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'streamlit', 'pandas', 'plotly', 'neo4j', 
        'google-generativeai', 'sentence-transformers',
        'openpyxl', 'rdflib'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall them with: pip install -r requirements_streamlit.txt")
        return False
    
    print("✅ All required packages are installed")
    return True

def create_directory_structure():
    """Create required directory structure"""
    directories = [
        "P&ID",
        "MSDS", 
        "Context for RAG",
        "Process Description",
        "Results",
        "api_cache",
        ".streamlit"
    ]
    
    print("📂 Creating directory structure...")
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"  ✅ {directory}/")
    
    # Create .streamlit/config.toml
    streamlit_config = """
[server]
port = 8501
address = "localhost"
maxUploadSize = 200

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[browser]
gatherUsageStats = false
"""
    
    with open(".streamlit/config.toml", "w") as f:
        f.write(streamlit_config)

def check_config_file():
    """Check if config.py exists and is properly configured"""
    if not os.path.exists("config.py"):
        print("❌ config.py not found!")
        print("Creating config.py from template...")
        
        # Create basic config template
        config_template = '''"""
HAZOP Analysis Configuration File
Copy this template and fill in your actual values.
"""

import os

# Neo4j Database Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password_here")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here")
GEMINI_MODEL_NAME = "gemini-1.5-pro"

# File Paths
ONTOLOGY_FILE_PATH = "HAZOP_Ontology_CLEAN.rdf"
PID_PATH = "P&ID/your_pid_file.cypher"
MSDS_DIRECTORY_PATH = "MSDS/"
PROCESS_DESCRIPTION_PATH = "Process Description/your_process_description.md"
GENERATED_PROCESS_DESCRIPTION_PATH = "Results/Generated_process_description.md"

# Context CSV Paths
PARAMETER_GUIDEWORD_CSV_PATH = "Context/Parameter_and_guideword.csv"
CAUSES_CSV_PATH = "Context/Causes.csv"
CONSEQUENCES_CSV_PATH = "Context/Consequences.csv"
SAFEGUARDS_CSV_PATH = "Context/Safeguard.csv"

# Output Paths
APPLICABLE_DEVIATIONS_PATH = "Results/Applicable_deviations.csv"
EXCEL_REPORT_PATH = "Results/HAZOP_Analysis_Equipment.xlsx"
ORIGINAL_HAZOP_REPORT_PATH = "Original_HAZOP_Report.csv"

# API Limits
MAX_API_CALLS_PER_RUN = 50
MAX_CONTEXT_LENGTH = 8000
MAX_MSDS_FILES = 10
'''
        
        with open("config.py", "w") as f:
            f.write(config_template)
        
        print("📝 config.py created! Please edit it with your actual values.")
        return False
    
    print("✅ config.py found")
    return True

def check_required_files():
    """Check if required files exist"""
    required_files = [
        "01_parsing_P&ID.py",
        "02_ontology_loader.py", 
        "03_semantic_enrichment.py",
        "05_Understanding_process_using_LLM.py",
        "06_Generate_applicable_deviations.py",
        "07_HAZOP_analysis.py",
        "08_verify_accuracy.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required pipeline scripts:")
        for file in missing_files:
            print(f"  - {file}")
        return False
    
    print("✅ All pipeline scripts found")
    return True

def launch_streamlit_app(mode="web"):
    """Launch the Streamlit application"""
    print(f"\n🚀 Launching HAZOP Analysis Platform in {mode} mode...")
    
    if mode == "web":
        app_file = "streamlit_app.py"
        if not os.path.exists(app_file):
            print(f"❌ {app_file} not found!")
            return False
        
        print("🌐 Starting web interface...")
        print("📝 The application will open in your default browser")
        print("🔗 URL: http://localhost:8501")
        print("\n" + "="*50)
        print("🛑 Press Ctrl+C to stop the application")
        print("="*50)
        
        try:
            subprocess.run([
                "streamlit", "run", app_file,
                "--server.port", "8501",
                "--server.address", "localhost"
            ])
        except KeyboardInterrupt:
            print("\n👋 Application stopped by user")
        except FileNotFoundError:
            print("❌ Streamlit not found! Install it with: pip install streamlit")
            return False
    
    elif mode == "cli":
        # CLI mode - run original main.py
        if os.path.exists("main.py"):
            print("🖥️ Running in command-line mode...")
            subprocess.run(["python", "main.py"])
        else:
            print("❌ main.py not found for CLI mode!")
            return False
    
    return True

def show_help():
    """Show help information"""
    help_text = """
🔧 HAZOP Analysis Platform Launcher

This launcher helps you set up and run the HAZOP analysis automation platform.

MODES:
  web     Launch the Streamlit web interface (default)
  cli     Run the original command-line version
  setup   Run setup and validation only
  help    Show this help message

EXAMPLES:
  python launcher.py              # Launch web interface
  python launcher.py --mode web   # Launch web interface
  python launcher.py --mode cli   # Run command-line version
  python launcher.py --mode setup # Setup and validate only

REQUIREMENTS:
  - Python 3.8 or higher
  - Neo4j database running
  - Required Python packages (see requirements_streamlit.txt)
  - Proper configuration in config.py

FIRST TIME SETUP:
  1. Run: python launcher.py --mode setup
  2. Edit config.py with your actual values
  3. Upload your data files through the web interface
  4. Run: python launcher.py

For more information, see the README.md file.
"""
    print(help_text)

def run_setup():
    """Run complete setup and validation"""
    print("🔧 Running HAZOP Platform Setup...")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Create directories
    create_directory_structure()
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Setup failed: Missing dependencies")
        print("Run: pip install -r requirements_streamlit.txt")
        return False
    
    # Check config
    config_exists = check_config_file()
    
    # Check pipeline scripts
    scripts_exist = check_required_files()
    
    print("\n" + "=" * 50)
    print("📋 Setup Summary:")
    print("=" * 50)
    
    if config_exists and scripts_exist:
        print("✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit config.py with your actual credentials")
        print("2. Upload your data files")
        print("3. Run: python launcher.py")
        return True
    else:
        print("❌ Setup incomplete - please resolve the issues above")
        return False

def main():
    """Main launcher function"""
    parser = argparse.ArgumentParser(description="HAZOP Analysis Platform Launcher")
    parser.add_argument(
        "--mode", 
        choices=["web", "cli", "setup", "help"],
        default="web",
        help="Launch mode (default: web)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "help":
        show_help()
        return
    
    if args.mode == "setup":
        run_setup()
        return
    
    # For web and cli modes, run basic checks first
    print("🔍 Running pre-launch checks...")
    
    check_python_version()
    
    if not check_dependencies():
        print("❌ Cannot launch: Missing dependencies")
        print("Run setup first: python launcher.py --mode setup")
        return
    
    if not check_config_file():
        print("❌ Cannot launch: Configuration incomplete")
        print("Please edit config.py with your actual values")
        return
    
    if not check_required_files():
        print("❌ Cannot launch: Missing pipeline scripts")
        return
    
    # Create directories if they don't exist
    create_directory_structure()
    
    # Launch the application
    success = launch_streamlit_app(args.mode)
    
    if not success:
        print("❌ Failed to launch application")
        sys.exit(1)

if __name__ == "__main__":
    main()