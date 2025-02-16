#!/usr/bin/env python3
"""
deepseek_name_request.py --- Extracts person's name from the OCR text via Deepseek model.
Version: 1.0.1

Reads OCR data from ./ocr/transcribed_json.json, sends a prompt to the Deepseek model
to identify only the person's name of the deceased, and saves results to
./deepseek/deepseek_names.json, then updates the global data file.
"""

import os
import json
import requests
from global_updater import update_global_file

def ensure_directory_exists(file_path):
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def load_ocr_data(ocr_file_path):
    with open(ocr_file_path, "r", encoding="utf-8") as file:
        return json.load(file)

def load_deepseek_name_responses(response_file_path):
    if os.path.exists(response_file_path):
        with open(response_file_path, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []
    return []

def build_name_prompt(ocr_record):
    ocr_data_str = json.dumps(ocr_record.get("ocr_text", ""), indent=2)
    prompt = (
        "Extract the full name of the deceased. Look for: Name of the deceased (in full): [Name]."
        "Return a JSON array with one object containing exactly the key: 'person_name'. "
        "Do not add explanations or extra text. No yapping.\n\n"
        "OCR TEXT:\n" + ocr_data_str
    )
    return prompt

def build_json_schema():
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string"}
            },
            "required": ["person_name"]
        }
    }

def send_generate_request(payload, url):
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

def parse_model_response(api_result):
    raw_response = api_result.get("response", "").strip()
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError as e:
        print("Failed to parse the 'response' field as JSON:", e)
        return raw_response

def save_name_responses(response_data, response_file_path):
    ensure_directory_exists(response_file_path)
    with open(response_file_path, "w", encoding="utf-8") as out_file:
        json.dump(response_data, out_file, indent=2)

def main():
    ocr_file_path = "./ocr/transcribed_json.json"
    response_file_path = "./deepseek/deepseek_names.json"

    ocr_data = load_ocr_data(ocr_file_path)
    name_responses = load_deepseek_name_responses(response_file_path)

    # 1) Remove any duplicates in name_responses itself (if they exist from older runs).
    unique_entries = {}
    for entry in name_responses:
        filename = entry.get("filename")
        if filename and filename not in unique_entries:
            unique_entries[filename] = entry
    name_responses = list(unique_entries.values())

    # 2) Build a set of already-processed filenames
    processed_files = {entry.get("filename") for entry in name_responses if "filename" in entry}

    url = "http://127.0.0.1:11434/api/generate"
    json_schema = build_json_schema()

    for record in ocr_data:
        filename = record.get("filename")
        if not filename:
            continue
        if filename in processed_files:
            print(f"Skipping already processed file: {filename}")
            continue

        print(f"Extracting name for file: {filename}")
        prompt = build_name_prompt(record)
        payload = {
            "model": "deepseek-r1:32b",
            "prompt": prompt,
            "stream": False,
            "format": json_schema
        }

        try:
            api_result = send_generate_request(payload, url)
            parsed_response = parse_model_response(api_result)

            if isinstance(parsed_response, list) and len(parsed_response) > 0:
                result_obj = parsed_response[0]
            elif isinstance(parsed_response, dict):
                result_obj = parsed_response
            else:
                result_obj = {}

            output_entry = {
                "filename": filename,
                "person_name": result_obj.get("person_name", "")
            }

            name_responses.append(output_entry)
            processed_files.add(filename)

            # Save to deepseek_names.json
            save_name_responses(name_responses, response_file_path)
            # Update the global file
            update_global_file(response_file_path)

            print(f"Name extraction for {filename} saved.")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while sending the request for file {filename}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for file {filename}: {e}")

if __name__ == "__main__":
    main()
