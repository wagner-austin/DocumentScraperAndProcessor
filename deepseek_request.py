#!/usr/bin/env python3
"""
deepseek_request.py --- Sends an HTTP request to the Deepseek model via Ollama,
extracting structured response for death_date, death_location, and cause_of_death.
Version: 1.1.4
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

def load_deepseek_responses(response_file_path):
    if os.path.exists(response_file_path):
        with open(response_file_path, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []
    return []

def build_prompt(ocr_record):
    ocr_data_str = json.dumps(ocr_record, indent=2)
    prompt = (
        "Extract the following details from the OCR record (if available):\n"
        "1. death_date, write the death date in Month Day, Year -- it should be between 1865 and 1867\n"
        "2. death_location, write a specific location or address of death\n"
        "3. cause_of_death, write a specific and succinct cause of death\n\n"
        "Return a JSON array with one object containing exactly these keys:\n"
        "  - death_date\n"
        "  - death_location\n"
        "  - cause_of_death\n\n"
        "Do not include any extra text. Be succinct and concise.\n\n"
        "OCR Record:\n" + ocr_data_str
    )
    return prompt

def build_json_schema():
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "death_date": {"type": "string"},
                "death_location": {"type": "string"},
                "cause_of_death": {"type": "string"}
            },
            "required": ["death_date", "death_location", "cause_of_death"]
        }
    }

def send_generate_request(payload, url):
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

def parse_model_response(api_result):
    raw_response = api_result.get("response", "").strip()
    try:
        parsed_response = json.loads(raw_response)
        return parsed_response
    except json.JSONDecodeError as e:
        print("Failed to parse the 'response' field as JSON:", e)
        return raw_response

def save_responses(response_data, response_file_path):
    ensure_directory_exists(response_file_path)
    with open(response_file_path, "w", encoding="utf-8") as out_file:
        json.dump(response_data, out_file, indent=2)

def main():
    ocr_file_path = "./ocr/transcribed_json.json"
    response_file_path = "./deepseek/deepseek_response.json"

    ocr_data = load_ocr_data(ocr_file_path)
    deepseek_responses = load_deepseek_responses(response_file_path)
    processed_files = {entry.get("filename") for entry in deepseek_responses if "filename" in entry}

    url = "http://127.0.0.1:11434/api/generate"
    json_schema = build_json_schema()

    for record in ocr_data:
        filename = record.get("filename")
        if not filename:
            continue
        if filename in processed_files:
            print(f"Skipping already processed file: {filename}")
            continue

        print(f"Processing OCR for file: {filename}")
        prompt = build_prompt(record)
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

            ordered_result = {
                "filename": filename,
                "death_date": result_obj.get("death_date", ""),
                "death_location": result_obj.get("death_location", ""),
                "cause_of_death": result_obj.get("cause_of_death", "")
            }

            deepseek_responses.append(ordered_result)
            processed_files.add(filename)

            save_responses(deepseek_responses, response_file_path)
            # Immediately update the global file
            update_global_file(response_file_path)

            print(f"Deepseek response for {filename} saved.")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while sending the request for file {filename}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for file {filename}: {e}")

if __name__ == "__main__":
    main()
