#!/usr/bin/env python3
"""
cholera_processor.py --- Processes cholera death records by copying PDFs and updating a JSON file.
Version: 1.2.0
"""

import os
import json
import shutil

GLOBAL_FILE = "./data/complete_data.json"

def process_cholera_deaths():
    """
    Processes the complete_data.json to filter out cholera death records,
    ensures that the ./cholera_positive directory contains only the PDFs corresponding
    to current cholera-positive records, copies any missing PDFs from ./death_certificates/,
    and overwrites the JSON file at ./data/cholera_deaths.json with the updated records.
    """
    cholera_pdf_dir = "./cholera_positive"
    os.makedirs(cholera_pdf_dir, exist_ok=True)

    # Load the complete_data.json file
    try:
        with open(GLOBAL_FILE, "r") as f:
            complete_data = json.load(f)
    except Exception as e:
        print("Error reading complete_data.json:", e)
        return

    # Filter records with cholera_death == "yes" (case-insensitive)
    cholera_records = [
        record for record in complete_data
        if record.get("cholera_death", "").lower() == "yes"
    ]

    # Build a set of valid base filenames from cholera_records
    valid_filenames = {record.get("filename", "") for record in cholera_records}

    # Remove any PDFs in cholera_pdf_dir that are not in the valid set
    for file in os.listdir(cholera_pdf_dir):
        if file.lower().endswith(".pdf"):
            base_filename = file[:-4]  # remove ".pdf"
            if base_filename not in valid_filenames:
                file_to_remove = os.path.join(cholera_pdf_dir, file)
                try:
                    os.remove(file_to_remove)
                    print(f"Removed outdated file: {file_to_remove}")
                except Exception as e:
                    print(f"Error removing file {file_to_remove}: {e}")

    # Copy the PDF files for cholera death records if they don't already exist
    for record in cholera_records:
        pdf_filename = record.get("filename", "") + ".pdf"  # Assumes PDF filenames follow this convention
        src_path = os.path.join("./death_certificates", pdf_filename)
        dst_path = os.path.join(cholera_pdf_dir, pdf_filename)
        if not os.path.exists(src_path):
            print(f"Source PDF not found: {src_path}")
            continue
        if os.path.exists(dst_path):
            print(f"PDF already exists, skipping: {dst_path}")
        else:
            try:
                shutil.copy2(src_path, dst_path)
                print(f"Copied {src_path} to {dst_path}")
            except Exception as e:
                print(f"Error copying {src_path} to {dst_path}: {e}")

    # Overwrite the JSON file with the updated cholera records
    cholera_json_path = "./data/cholera_deaths.json"
    try:
        with open(cholera_json_path, "w") as f:
            json.dump(cholera_records, f, indent=4)
        print(f"Cholera JSON file updated: {cholera_json_path}")
    except Exception as e:
        print(f"Error writing {cholera_json_path}: {e}")

if __name__ == "__main__":
    process_cholera_deaths()
