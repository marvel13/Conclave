import json
from uuid import uuid4

import numpy as np
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd

DB_PARAMS = {
    "dbname": "cardinals_db",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5432",
}

with open("data/cardinals_with_attributes_cleaned.json", "r") as f:
    cardinals_data = json.load(f)

ATTRIBUTES = [
    "conservative",  # From theological_stance
    "reform_leaning",  # From theological_stance
    "lgbtq_policies",  # From issue_positions
    "environmentalism",  # From issue_positions
]

def create_vector(cardinal):
    """
    Create a 4-element vector from a cardinal's analysis_results data.

    Args:
        cardinal (dict): A dictionary containing cardinal data with 'analysis_results' key.

    Returns:
        list: A 4-element list of floats for conservative, reform_leaning, lgbtq_policies, environmentalism ratings.
    """
    vector = []

    # Ensure cardinal is a dictionary
    if not isinstance(cardinal, dict):
        print(f"Error: Expected a dictionary, got {type(cardinal)}")
        return vector  # Return empty vector if invalid input

    # Get analysis_results, default to empty dict if missing
    analysis = cardinal.get("analysis_results", {})

    # Extract theological_stance ratings
    theo_stance = analysis.get("theological_stance", {})
    vector.append(float(theo_stance.get("conservative", {}).get("rating", 3.0)))
    vector.append(float(theo_stance.get("reform_leaning", {}).get("rating", 3.0)))

    # Extract issue_positions ratings
    issue_pos = analysis.get("issue_positions", {})
    vector.append(float(issue_pos.get("lgbtq_policies", {}).get("rating", 3.0)))
    vector.append(float(issue_pos.get("environmentalism", {}).get("rating", 3.0)))

    return vector

def extract_attributes(cardinal):
    """
    Extract the attributes from a cardinal's data.
    
    Args:
        cardinal (dict): A dictionary containing cardinal data with 'attributes' key.
        
    Returns:
        list: A list of dictionaries with issue_title and label for each attribute.
    """
    attributes = []
    
    # Extract attributes from the cardinal data
    for attr in cardinal.get("attributes", []):
        if "issue_title" in attr and "label" in attr:
            attributes.append({
                "issue_title": attr["issue_title"],
                "label": attr["label"]
            })
    
    return attributes

cardinal_vectors = []
for cardinal in cardinals_data:
    vector = create_vector(cardinal)
    attributes = extract_attributes(cardinal)
    
    # Convert attributes list to JSON string for storage
    attributes_json = json.dumps(attributes)
    
    if len(vector) != 4:
        print(f"Warning: Invalid vector for cardinal {cardinal.get('name', 'Unknown')}: {vector}")
        continue
    cardinal_vectors.append((
        cardinal.get('name', ''),
        cardinal.get('nation', ''),
        cardinal.get('continent', ''),
        cardinal.get('position', ''),
        cardinal.get('voting_status', ''),
        cardinal.get('created_by', ''),
        int(cardinal.get('age', 0)),
        vector,
        attributes_json  # Add the attributes JSON string
    ))

try:
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    cur.execute("""
        CREATE EXTENSION IF NOT EXISTS vector;
        DROP TABLE IF EXISTS cardinals;
        CREATE TABLE cardinals (
            id UUID PRIMARY KEY,
            name TEXT NOT NULL,
            nation TEXT,
            continent TEXT,
            position TEXT,
            voting_status TEXT,
            created_by TEXT,
            age INTEGER,
            attribute_vector VECTOR(4),
            attributes JSONB  -- Store the attributes as JSONB for easier querying
        );
    """)
    insert_query = """
        INSERT INTO cardinals (id, name, nation, continent, position, voting_status, created_by, age, attribute_vector, attributes)
        VALUES %s
    """
    data = [(str(uuid4()), *cv) for cv in cardinal_vectors]
    execute_values(cur, insert_query, data)

    cur.execute("CREATE INDEX ON cardinals USING ivfflat (attribute_vector vector_cosine_ops) WITH (lists = 100);")
    conn.commit()

    def find_similar_cardinals(cardinal_name, top_k=5):
        """Find cardinals with similar attributes"""
        cur.execute("SELECT attribute_vector FROM cardinals WHERE name = %s", (cardinal_name,))
        result = cur.fetchone()
        if not result:
            return f"Cardinal '{cardinal_name}' not found."
        query_vector = result[0]

        # Print the vector for the queried cardinal
        print(f"Vector for {cardinal_name}: {query_vector}")

        cur.execute("""
            SELECT name, nation, continent, position, voting_status, created_by, age,
                   attribute_vector, attributes, 1 - (attribute_vector <=> %s::vector) AS similarity
            FROM cardinals
            WHERE name != %s
            ORDER BY similarity DESC
            LIMIT %s
        """, (query_vector, cardinal_name, top_k))

        results = cur.fetchall()
        output = f"Cardinals most similar to {cardinal_name}:\n"
        for row in results:
            name, nation, continent, position, voting_status, created_by, age, vector, attributes, similarity = row
            
            # Parse attributes for readable output
            parsed_attrs = []
            try:
                attrs = json.loads(attributes)
                for attr in attrs:
                    parsed_attrs.append(f"{attr['issue_title']}: {attr['label']}")
            except (json.JSONDecodeError, TypeError):
                parsed_attrs = ["No attributes available"]
            
            output += (f"- {name} (Nation: {nation}, Continent: {continent}, Position: {position}, "
                      f"Voting Status: {voting_status}, Created By: {created_by}, Age: {age}, "
                      f"Vector: {vector}, Similarity: {similarity:.4f})\n")
            output += f"  Attributes: {', '.join(parsed_attrs)}\n"
            
        return output

    query_cardinal = "Cardinal João Braz de Aviz"
    print(find_similar_cardinals(query_cardinal))

    # Export data to CSV
    cur.execute("SELECT * FROM cardinals")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    df = pd.DataFrame(rows, columns=columns)
    df.to_csv('cardinals_data.csv', index=False)
    print("Data exported to cardinals_data.csv")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if cur:
        cur.close()
    if conn:
        conn.close()