#!/usr/bin/env python3
"""
Extract url, title, content, and year from Bill's Black Box articles JSON files.
Creates cleaned versions with only the relevant text fields.
"""

import json
import os
from pathlib import Path

def extract_year_from_filename(filename):
    """Extract year from filename like '2024_Title.json'"""
    year = filename.split('_')[0]
    return year if year.isdigit() else "unknown"

def extract_relevant_fields(json_file_path):
    """Extract url, title, content, and year from JSON file"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    filename = os.path.basename(json_file_path)
    year = extract_year_from_filename(filename)

    # Extract only the relevant fields
    extracted = {
        "url": data.get("url", ""),
        "title": data.get("title", ""),
        "year": year,
        "content": data.get("content", "")
    }

    return extracted

def main():
    # Define paths
    input_dir = Path("/home/brian/sam_gov/bills_blackbox_articles")
    output_dir = Path("/home/brian/sam_gov/bills_blackbox_articles_extracted")

    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)

    # Get all JSON files
    json_files = list(input_dir.glob("*.json"))

    print(f"Found {len(json_files)} JSON files to process")

    processed = 0
    errors = 0

    for json_file in json_files:
        try:
            # Extract relevant fields
            extracted_data = extract_relevant_fields(json_file)

            # Create output filename (same as input)
            output_file = output_dir / json_file.name

            # Write extracted data to new file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)

            processed += 1

            if processed % 10 == 0:
                print(f"Processed {processed} files...")

        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")
            errors += 1

    print(f"\n{'='*60}")
    print(f"Extraction complete!")
    print(f"Successfully processed: {processed}")
    print(f"Errors: {errors}")
    print(f"Output directory: {output_dir}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
