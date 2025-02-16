#!/usr/bin/env python3
"""
pipeline.py --- Runs the full processing pipeline sequentially by importing modules,
updates the global complete_data.json, and calls the cholera processing module.
Version: 1.0.5
"""

import importlib
import os
import json
import time
import traceback
from global_updater import update_global_file
import cholera_processor  # Import the separate cholera processing module

# File paths for the various outputs
SAVED_FILES = "./records/saved_files.json"                       # Output from historical_vital_records_downloader.py
OCR_JSON = "./ocr/transcribed_json.json"                         # Output from document_ai_processor.py
DEEPOSEEK_NAMES_JSON = "./deepseek/deepseek_names.json"          # Output from deepseek_name_request.py
DEEPOSEEK_JSON = "./deepseek/deepseek_response.json"             # Output from deepseek_request.py
DEEPOSEEK_CHOLERA_JSON = "./deepseek/deepseek_yes_no_response.json"  # Output from deepseek_cholera_request.py
GLOBAL_FILE = "./data/complete_data.json"

# Ensure the global data directory exists
os.makedirs(os.path.dirname(GLOBAL_FILE), exist_ok=True)

def run_module(module_name):
    """
    Imports the given module and calls its main() function.
    """
    print(f"Running {module_name}...")
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, 'main'):
            module.main()
        else:
            print(f"Module {module_name} does not have a main() function.")
    except Exception as e:
        print(f"Error running {module_name}: {e}")
        traceback.print_exc()
        exit(1)
    print(f"{module_name} completed.\n")
    # Small delay to ensure file writes are finished
    time.sleep(1)

def main():
    # Step 1: Run historical_vital_records_downloader.py
    run_module("historical_vital_records_downloader")

    # Step 2: Run document_ai_processor.py
    run_module("document_ai_processor")

    # Step 2.5: Run deepseek_name_request.py
    run_module("deepseek_name_request")

    # Step 3: Run deepseek_request.py
    run_module("deepseek_request")

    # Step 4: Run deepseek_cholera_request.py
    run_module("deepseek_cholera_request")

    print("Pipeline processing complete. Global file updated at:", GLOBAL_FILE)
    
    # Run cholera processing module to copy PDFs and update JSON with cholera death records
    cholera_processor.process_cholera_deaths()

if __name__ == "__main__":
    main()
