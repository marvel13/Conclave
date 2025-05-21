import json
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    
    Args:
        vector_value: Vector from PostgreSQL (could be string or special type)
        
    Returns:
        List of floats
    """
    if isinstance(vector_value, list):
        return [float(x) for x in vector_value]
    if hasattr(vector_value, '__iter__') and not isinstance(vector_value, str):
        return [float(x) for x in vector_value]
    if isinstance(vector_value, str):
        clean_vector = re.sub(r'[\[\]\(\)]', '', vector_value)
        return [float(x.strip()) for x in clean_vector.split(',')]
    print(f"Warning: Unexpected vector format: {type(vector_value)}, value: {vector_value}")
    return [0.0, 0.0, 0.0, 0.0]

def parse_attributes(attributes_json):
    """
    Parse attributes JSON into a more readable format for hover text.
    
    Args:
        attributes_json: JSON string or JSONB from PostgreSQL
        
    Returns:
        String formatted for hover display
    """
    try:
        if isinstance(attributes_json, (dict, list)):
            attributes = attributes_json
        else:
            attributes = json.loads(attributes_json)
        attr_strings = []
        for attr in attributes:
            if "issue_title" in attr and "rating" in attr:
                attr_strings.append(f"<b>{attr['issue_title'].capitalize()}</b>: {float(attr['rating']):.1f}")
        return "<br>".join(attr_strings)
    except (json.JSONDecodeError, TypeError):
        return "No attributes data"

def visualize_3d_clusters():
    # 1. Get data from PostgreSQL
    df = fetch_vectors()
    if df.empty:
        print("No data retrieved from database")
        return None
    
    # 2. Convert vectors to numpy array
    df['parsed_vector'] = df['vector'].apply(parse_vector)
    df['formatted_attributes'] = df['attributes'].apply(parse_attributes)
    
    # Debug info
    print(f"Sample raw vector: {df['vector'].iloc[0]}")
    print(f"Sample parsed vector: {df['parsed_vector'].iloc[0]}")
    print(f"Sample attributes: {df['attributes'].iloc[0]}")
    print(f"Sample formatted attributes: {df['formatted_attributes'].iloc[0]}")
    
    # Check vector lengths
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
    
    # 5. Create dataframe for plotting
    plot_df = pd.DataFrame({
        'x': umap_3d[:, 0],
        'y': umap_3d[:, 1],
        'z': umap_3d[:, 2],
        'name': df['name'],
        'nation': df['nation'],
        'continent': df['continent'],
        'attributes': df['formatted_attributes'],
        'cluster': clusters.astype(str)
    })
    
    # 6. Create interactive 3D plot
    fig = px.scatter_3d(
        data_frame=plot_df,
        x='x',
        y='y',
        z='z',
        color='cluster',
        color_discrete_sequence=px.colors.qualitative.Bold,
        hover_name='name',
        hover_data={
            'nation': True,
            'continent': True,
            'attributes': True,
            'x': False,
            'y': False,
            'z': False,
            'cluster': True
        },
        labels={
            'x': 'UMAP Component 1',
            'y': 'UMAP Component 2',
            'z': 'UMAP Component 3',
            'cluster': 'Cluster',
            'attributes': 'Theological & Social Positions'
        },
        title='3D Clustering of Cardinals by Theological and Social Stances'
    )
    
    # 7. Customize layout
    fig.update_traces(
        marker=dict(
            size=8,
            opacity=0.8,
            line=dict(width=1, color='DarkSlateGrey')
        ),
        selector=dict(mode='markers')
    )
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                title=dict(
                    text='UMAP Component 1',
                    font=dict(size=14, family='Arial')
                ),
                backgroundcolor='white',
                gridcolor='lightgrey',
                tickfont=dict(size=12)
            ),
            yaxis=dict(
                title=dict(
                    text='UMAP Component 2',
                    font=dict(size=14, family='Arial')
                ),
                backgroundcolor='white',
                gridcolor='lightgrey',
                tickfont=dict(size=12)
            ),
            zaxis=dict(
                title=dict(
                    text='UMAP Component 3',
                    font=dict(size=14, family='Arial')
                ),
                backgroundcolor='white',
                gridcolor='lightgrey',
                tickfont=dict(size=12)
            ),
            bgcolor='white'
        ),
        title=dict(
            text='3D Clustering of Cardinals by Theological and Social Stances<br><i>Hover to see details; click and drag to rotate</i>',
            x=0.5,
            xanchor='center',
            font=dict(size=18, family='Arial', color='black')
        ),
        legend=dict(
            title='Cluster',
            font=dict(size=12),
            bgcolor='rgba(255, 255, 255, 0.7)',
            bordercolor='grey',
            borderwidth=1
        ),
        margin=dict(l=0, r=0, t=80, b=0),
        paper_bgcolor='white',
        plot_bgcolor='white',
        hovermode='closest'
    )
    
    # 8. Add dropdown for filtering by continent
    buttons = []
    continents = plot_df['continent'].unique()
    buttons.append(dict(
        label='All',
        method='update',
        args=[{
            'visible': [True] * len(plot_df),
            'title': '3D Clustering of Cardinals by Theological and Social Stances<br><i>All Continents</i>'
        }]
    ))
    for continent in continents:
        mask = plot_df['continent'] == continent
        buttons.append(dict(
            label=continent,
            method='update',
            args=[{
                'visible': mask.tolist(),
                'title': f'3D Clustering of Cardinals by Theological and Social Stances<br><i>Continent: {continent}</i>'
            }]
        ))

    fig.update_layout(
        updatemenus=[
            dict(
                buttons=buttons,
                direction='down',
                showactive=True,
                x=0.1,
                xanchor='left',
                y=1.1,
                yanchor='top',
                font=dict(size=12)
            )
        ]
    )
    
    # 9. Add annotation for context
    fig.add_annotation(
        text="Based on ratings for Conservative, Reform-Leaning, LGBTQ Policies, and Environmentalism",
        xref="paper", yref="paper",
        x=0.5, y=-0.1,
        showarrow=False,
        font=dict(size=10, color='grey'),
        xanchor='center'
    )
    
    return fig

if __name__ == "__main__":
    fig = visualize_3d_clusters()
    if fig:
        fig.show()
        fig.write_html('cardinals_3d_clustering.html', include_plotlyjs='cdn')
        print("Plot exported as cardinals_3d_clustering.html")
    else:
        print("Failed to generate visualization")