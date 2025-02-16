#!/usr/bin/env python3
"""
deepseek_cholera_request.py --- Determines if cause of death is related to cholera via fuzzy keyword search.
Version: 1.3.0

Processes deepseek_response.json one record at a time, checking the cause_of_death for cholera-related keywords
using fuzzy matching to account for minor misspellings, and adds the cause_of_death and cholera_death result ('yes', 'no', or 'unknown') to the output.
"""

import os
import json
import re
import difflib
from global_updater import update_global_file

def ensure_directory_exists(file_path):
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def load_json_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []
    return []

def save_responses(response_data, file_path):
    ensure_directory_exists(file_path)
    with open(file_path, "w", encoding="utf-8") as out_file:
        json.dump(response_data, out_file, indent=2)

def fuzzy_in_text(keyword, text, threshold=0.8):
    """
    Returns True if the keyword is found in the text either as an exact substring
    or if any token in the text is similar to the keyword based on the given threshold.
    """
    # Exact substring check
    if keyword in text:
        return True

    # Tokenize text by non-word characters (ignores punctuation)
    words = re.split(r'\W+', text)
    for word in words:
        if difflib.SequenceMatcher(None, word, keyword).ratio() >= threshold:
            return True
    return False

def check_cholera_keywords(cause):
    """
    Check the cause_of_death string for cholera-related keywords using fuzzy matching.
    
    Returns:
        'yes' if a cholera keyword is found,
        'no' if any negative keyword is found,
        'unknown' if none of the keywords are found.
    """
    if not cause:
        return "unknown"
    cause_lower = cause.lower()
    
    # Negative keywords that indicate the death is not related to cholera.
    negative_keywords = [
        "hanging", "convulsions", "head injury", "typhoid fever", "diptheria", "epilepsy", "old age"
    ]
    for neg in negative_keywords:
        if fuzzy_in_text(neg, cause_lower, threshold=0.8):
            return "no"
    
    # Positive keywords that indicate cholera-related death.
    positive_keywords = [
        "cholera", "asiatic cholera", "cholera morbus", "cholera infantum",
        "chronic diarrhea", "diarrhoea", "diarrhea", "vomiting", "exhaustion"
    ]
    for pos in positive_keywords:
        if fuzzy_in_text(pos, cause_lower, threshold=0.8):
            return "yes"
    
    return "unknown"

def main():
    input_file = "./deepseek/deepseek_response.json"
    output_file = "./deepseek/deepseek_yes_no_response.json"

    deepseek_records = load_json_data(input_file)
    yes_no_responses = load_json_data(output_file)

    processed_files = {entry.get("filename") for entry in yes_no_responses if "filename" in entry}

    for record in deepseek_records:
        filename = record.get("filename")
        if not filename:
            continue
        if filename in processed_files:
            print(f"Skipping already processed file: {filename}")
            continue

        print(f"Processing cholera check for file: {filename}")
        cause = record.get("cause_of_death", "")
        cholera_death = check_cholera_keywords(cause)

        output_entry = {
            "filename": filename,
            "cause_of_death": cause,
            "cholera_death": cholera_death
        }

        yes_no_responses.append(output_entry)
        processed_files.add(filename)

        save_responses(yes_no_responses, output_file)
        update_global_file(output_file)

        print(f"Cholera check response for {filename} saved.")

if __name__ == "__main__":
    main()
