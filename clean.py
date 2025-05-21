import json

# Load the JSON data
with open('data/cardinals_with_attributes_attributes_cleaned.json', 'r') as file:
    data = json.load(file)

# Process each cardinal's attributes
for cardinal in data:
    # Filter out attributes with "Unknown" label
    cardinal['attributes'] = [
        attr for attr in cardinal['attributes'] 
        if attr.get('label') != 'Unknown'
    ]

# Save the modified data back to a JSON file
with open('data/cardinals_with_attributes_cleaned.json', 'w') as file:
    json.dump(data, file, indent=4)

print("Attributes with 'Unknown' label have been removed and saved to 'cardinals_with_attributes_cleaned.json'")