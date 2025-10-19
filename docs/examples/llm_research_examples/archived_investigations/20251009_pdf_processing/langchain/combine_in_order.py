#!/usr/bin/env python3
"""
Combine all page CSV files in proper page order
"""
import csv
import os

def main():
    """Combine all page CSV files in order"""
    
    all_witnesses = []
    
    # Read each page in order
    for page_num in range(1, 14):  # Pages 1-13
        csv_file = f"page_{page_num:02d}_witnesses.csv"
        
        if os.path.exists(csv_file):
            print(f"Reading {csv_file}...")
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                witnesses = list(reader)
                all_witnesses.extend(witnesses)
                print(f"  Added {len(witnesses)} witnesses")
        else:
            print(f"  ⚠️  {csv_file} not found")
    
    # Save combined file in page order
    output_file = "all_witnesses_page_order.csv"
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['ID', 'Last_Name', 'First_Name', 'Country', 'Information', 'Deceased', 'Public']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_witnesses)
    
    print(f"\n✅ Combined {len(all_witnesses)} witnesses in page order")
    print(f"📄 Saved to: {output_file}")
    
    # Show first and last few witnesses
    print(f"\n📝 FIRST 5 WITNESSES:")
    for i, witness in enumerate(all_witnesses[:5]):
        print(f"  {i+1}. ID {witness['ID']}: {witness['First_Name']} {witness['Last_Name']}")
    
    print(f"\n📝 LAST 5 WITNESSES:")
    for i, witness in enumerate(all_witnesses[-5:], len(all_witnesses)-4):
        print(f"  {i}. ID {witness['ID']}: {witness['First_Name']} {witness['Last_Name']}")

if __name__ == "__main__":
    main()