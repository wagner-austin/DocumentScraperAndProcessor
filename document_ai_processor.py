#!/usr/bin/env python3
"""
document_ai_processor.py --- Process PDFs with Document AI and save OCR results.
Version: 1.1.2

This script reads PDF files from the './death_certificates' directory,
sends them to a Document AI endpoint for OCR, and saves the result to
'./ocr/transcribed_json.json'. Then updates the global file.
"""

import os
import base64
import json
import requests
import google.auth
import google.auth.transport.requests
from global_updater import update_global_file

def get_access_token():
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    return credentials.token

def process_pdf(file_path, access_token, endpoint_url):
    with open(file_path, "rb") as f:
        file_content = f.read()
    encoded_content = base64.b64encode(file_content).decode("utf-8")

    payload = {
        "rawDocument": {
            "content": encoded_content,
            "mimeType": "application/pdf"
        }
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(endpoint_url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Error processing {file_path}: {response.status_code} - {response.text}")
        return None

    response_data = response.json()
    ocr_text = response_data.get("document", {}).get("text", "")
    return ocr_text

def main():
    endpoint_url = "https://us-documentai.googleapis.com/v1/projects/66601296107/locations/us/processors/b33f41abbc1016f2:process"
    directory = "./death_certificates"
    output_dir = "./ocr"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "transcribed_json.json")

    existing_results = []
    processed_files = set()
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            try:
                existing_results = json.load(f)
                processed_files = {os.path.splitext(item.get("filename", ""))[0] for item in existing_results}
            except json.JSONDecodeError:
                existing_results = []

    access_token = get_access_token()
    all_results = existing_results[:]

    for filename in os.listdir(directory):
        if filename.lower().endswith(".pdf"):
            file_base = os.path.splitext(filename)[0]
            if file_base in processed_files:
                print(f"Skipping already processed file: {file_base}")
                continue

            file_path = os.path.join(directory, filename)
            print(f"Processing file: {filename}")
            ocr_text = process_pdf(file_path, access_token, endpoint_url)
            if ocr_text is not None:
                print("Filename:", file_base)
                print("OCR Text:")
                print(ocr_text)
                print("=" * 50)
                result = {
                    "filename": file_base,
                    "ocr_text": ocr_text
                }
                all_results.append(result)
                processed_files.add(file_base)

                # Write to transcribed_json.json
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(all_results, f, indent=4)

                # Update the global file
                update_global_file(output_file)

    print(f"OCR results saved to {output_file}")

if __name__ == "__main__":
    main()
