#!/usr/bin/env python3
"""
Add the missing blank row and do row-by-row comparison
"""
import csv

def add_missing_witness():
    """Add the missing blank witness ID 10870 to the GPT-5 file"""
    
    # Read all current witnesses
    witnesses = []
    with open("all_witnesses_page_order.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        witnesses = list(reader)
    
    # Find where to insert the blank row (before 10387)
    insert_index = None
    for i, witness in enumerate(witnesses):
        if witness['ID'] == '10387':
            insert_index = i
            break
    
    if insert_index is not None:
        # Insert the blank witness 10870
        blank_witness = {
            'ID': '10870',
            'Last_Name': '',
            'First_Name': '',
            'Country': '',
            'Information': '',
            'Deceased': '',
            'Public': ''
        }
        witnesses.insert(insert_index, blank_witness)
        print(f"✓ Inserted blank witness 10870 before witness 10387 at position {insert_index}")
    else:
        print("✗ Could not find witness 10387 to insert before")
        return False
    
    # Save the updated file
    with open("all_witnesses_complete.csv", 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['ID', 'Last_Name', 'First_Name', 'Country', 'Information', 'Deceased', 'Public']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(witnesses)
    
    print(f"✓ Saved complete file with {len(witnesses)} witnesses")
    return True

def compare_row_by_row():
    """Compare row by row ignoring page numbers"""
    
    # Read original file
    original = {}
    with open("greer_dpia_witness_list_full_From_sigint.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            original[row['_pk_Contact_ID']] = {
                'Last_Name': row['Name_Last'],
                'First_Name': row['Name_First'], 
                'Country': row['Country'],
                'Information': row['Information'],
                'Deceased': row['Deceased'],
                'Public': row['Public']
            }
    
    # Read GPT-5 file
    gpt5 = {}
    with open("all_witnesses_complete.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            gpt5[row['ID']] = {
                'Last_Name': row['Last_Name'],
                'First_Name': row['First_Name'],
                'Country': row['Country'], 
                'Information': row['Information'],
                'Deceased': row['Deceased'],
                'Public': row['Public']
            }
    
    # Compare each row
    differences = []
    total_rows = 0
    
    for id in sorted(original.keys()):
        total_rows += 1
        
        if id not in gpt5:
            differences.append(f"ID {id}: Missing from GPT-5 file")
            continue
            
        orig_row = original[id]
        gpt5_row = gpt5[id]
        
        row_diffs = []
        for field in ['Last_Name', 'First_Name', 'Country', 'Information', 'Deceased', 'Public']:
            orig_val = orig_row[field].strip()
            gpt5_val = gpt5_row[field].strip()
            
            if orig_val != gpt5_val:
                row_diffs.append(f"{field}: '{orig_val}' → '{gpt5_val}'")
        
        if row_diffs:
            differences.append(f"ID {id}:")
            for diff in row_diffs:
                differences.append(f"  {diff}")
    
    print(f"\n📊 COMPARISON RESULTS:")
    print(f"Total rows compared: {total_rows}")
    print(f"Rows with differences: {len([d for d in differences if not d.startswith('  ')])}")
    
    if differences:
        print(f"\n📝 DIFFERENCES FOUND:")
        for diff in differences[:50]:  # Show first 50 differences
            print(diff)
        
        if len(differences) > 50:
            print(f"\n... and {len(differences) - 50} more differences")
    else:
        print(f"\n✅ All rows match perfectly!")

def main():
    print("🔍 Adding missing witness and comparing files...")
    
    if add_missing_witness():
        compare_row_by_row()

if __name__ == "__main__":
    main()