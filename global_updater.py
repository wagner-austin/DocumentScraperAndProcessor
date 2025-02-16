#!/usr/bin/env python3
"""
global_updater.py --- Utility to update the global data file.
Version: 1.0.0

This module centralizes the logic needed to load, merge, and save updates
to a global JSON file that holds consolidated data from other scripts.
"""

import os
import json

GLOBAL_FILE = "./data/complete_data.json"

def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_json(data, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def merge_records(existing, new, key_field="filename", rename_key=None):
    """
    Merge a list of new records into the existing dictionary (keyed by filename).
    Optionally rename a key from the new records (e.g., 'output filename' -> 'filename').
    """
    for record in new:
        if rename_key and rename_key in record:
            record["filename"] = record.pop(rename_key)
        fname = record.get("filename")
        if not fname:
            continue

        if fname in existing:
            existing[fname].update(record)
        else:
            # Initialize known keys with empty strings for consistency.
            merged = {
                "filename": fname,
                "person_name": "",
                "certificate_url": "",
                "ocr_text": "",
                "death_date": "",
                "death_location": "",
                "cause_of_death": "",
                "cholera_death": ""
            }
            merged.update(record)
            existing[fname] = merged
    return existing

def update_global_file(source_file, rename_key=None):
    """
    Loads data from a source JSON file, merges it into the global complete_data.json,
    and writes the updated data back out.
    """
    global_data = load_json(GLOBAL_FILE)
    global_dict = {entry.get("filename"): entry for entry in global_data if entry.get("filename")}

    source_data = load_json(source_file)
    updated_dict = merge_records(global_dict, source_data, rename_key=rename_key)

    merged_list = list(updated_dict.values())
    save_json(merged_list, GLOBAL_FILE)
    print(f"[global_updater] Updated global file from {source_file}")
