import json
import re

import numpy as np
import pandas as pd
import plotly.express as px
import psycopg2
from sklearn.cluster import KMeans
from umap import UMAP

DB_PARAMS = {
    "dbname": "cardinals_db",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5432",
}

def fetch_vectors():
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        cur.execute("""
            SELECT name, nation, continent, attribute_vector, attributes
            FROM cardinals
        """)
        results = cur.fetchall()
        return pd.DataFrame(results, columns=['name', 'nation', 'continent', 'vector', 'attributes'])
    except Exception as e:
        print(f"Database error: {e}")
        return pd.DataFrame()
    finally:
        if cur: cur.close()
        if conn: conn.close()

def parse_vector(vector_value):
    """
    Parse a PostgreSQL vector into a list of floats.
    
    The PostgreSQL pgvector extension returns vectors in a format that needs 
    to be converted to Python lists of floats.
    
    Args:
        vector_value: Vector from PostgreSQL (could be string or special type)
        
    Returns:
        List of floats
    """
    # If it's already a list, return it
    if isinstance(vector_value, list):
        return [float(x) for x in vector_value]
    
    # If it's a special pgvector type, convert it properly
    if hasattr(vector_value, '__iter__') and not isinstance(vector_value, str):
        return [float(x) for x in vector_value]
    
    # If it's a string representation like '[1,2,3,4]' or '(1,2,3,4)'
    if isinstance(vector_value, str):
        # Remove brackets/parentheses and split by comma
        clean_vector = re.sub(r'[\[\]\(\)]', '', vector_value)
        return [float(x.strip()) for x in clean_vector.split(',')]
    
    # If none of the above work, print debug info and return default
    print(f"Warning: Unexpected vector format: {type(vector_value)}, value: {vector_value}")
    return [0.0, 0.0, 0.0, 0.0]  # Default fallback

def parse_attributes(attributes_json):
    """
    Parse attributes JSON into a more readable format for hover text.
    
    Args:
        attributes_json: JSON string or JSONB from PostgreSQL
        
    Returns:
        String formatted for hover display
    """
    try:
        # If it's already a dict/list (PostgreSQL JSONB might be returned as dict)
        if isinstance(attributes_json, (dict, list)):
            attributes = attributes_json
        else:
            # Otherwise try to parse it as JSON string
            attributes = json.loads(attributes_json)
        
        # Create formatted string of attribute information
        attr_strings = []
        for attr in attributes:
            if "issue_title" in attr and "label" in attr:
                attr_strings.append(f"{attr['issue_title']}: {attr['label']}")
        
        return "<br>".join(attr_strings)
    except (json.JSONDecodeError, TypeError):
        return "No attributes data"

def visualize_3d_clusters():
    # 1. Get data from PostgreSQL
    df = fetch_vectors()
    if df.empty:
        print("No data retrieved from database")
        return
    
    # 2. Convert vectors to numpy array properly
    # Create a new column with properly parsed vectors
    df['parsed_vector'] = df['vector'].apply(parse_vector)
    
    # Parse attributes for hover text
    df['formatted_attributes'] = df['attributes'].apply(parse_attributes)
    
    # Print some debug info
    print(f"Sample raw vector: {df['vector'].iloc[0]}")
    print(f"Sample parsed vector: {df['parsed_vector'].iloc[0]}")
    print(f"Sample attributes: {df['attributes'].iloc[0]}")
    print(f"Sample formatted attributes: {df['formatted_attributes'].iloc[0]}")
    
    # Check if vectors are valid
    vector_lengths = df['parsed_vector'].apply(len)
    if not all(length == 4 for length in vector_lengths):
        print(f"Warning: Not all vectors have length 4. Lengths: {vector_lengths.value_counts()}")
        
    # 3. Dimensionality reduction with UMAP
    reducer = UMAP(n_components=3, random_state=42)
    vectors_array = np.array(df['parsed_vector'].tolist())
    umap_3d = reducer.fit_transform(vectors_array)
    
    # 4. Cluster identification using K-Means
    kmeans = KMeans(n_clusters=4, random_state=42)
    clusters = kmeans.fit_predict(vectors_array)
    
    # 5. Create a dataframe with the UMAP components and all data
    plot_df = pd.DataFrame({
        'x': umap_3d[:, 0],
        'y': umap_3d[:, 1],
        'z': umap_3d[:, 2],
        'name': df['name'],
        'nation': df['nation'],
        'continent': df['continent'],
        'attributes': df['formatted_attributes'],
        'cluster': clusters.astype(str)  # Convert to string for better legend
    })
    
    # 6. Create interactive 3D plot using the dataframe
    fig = px.scatter_3d(
        data_frame=plot_df,
        x='x',
        y='y',
        z='z',
        color='cluster',
        hover_name='name',
        hover_data={
            'nation': True,
            'continent': False,
            'attributes': True,
            'x': False,
            'y': False,
            'z': False,
            'cluster': True
        },
        labels={
            'x': 'UMAP Axis 1', 
            'y': 'UMAP Axis 2', 
            'z': 'UMAP Axis 3', 
            'cluster': 'Cluster',
            'attributes': 'Stance & Positions'
        },
        title='Cardinal Theological Stance Clustering'
    )
    
    return fig

if __name__ == "__main__":
    fig = visualize_3d_clusters()
    if fig:
        fig.show()
    else:
        print("Failed to generate visualization")