import json
import re

def clean_json_file(input_path, output_path):
    print(f"🧹 Cleaning {input_path}...")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        raw_data = f.read()

    # This regex removes illegal control characters (00-1F) 
    # but keeps common ones like newlines and tabs if they are properly escaped.
    # It specifically targets the 'invalid control characters' that break json.load()
    clean_data = re.sub(r'[\x00-\x1F\x7F]', '', raw_data)

    try:
        # Validate that it's now proper JSON
        data = json.loads(clean_data)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"✨ Success! Cleaned data saved to {output_path}")
    except json.JSONDecodeError as e:
        print(f"❌ Still hitting an error: {e}")
        print("This usually means there is a missing comma or a stray quote.")

if __name__ == "__main__":
    clean_json_file('data/catalog.json', 'data/catalog.json')