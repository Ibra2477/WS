import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
import plotly.express as px
from sklearn.metrics import silhouette_score
from collections import Counter
import umap.umap_ as umap
import re

# --- CONFIGURATION ---
PREFERRED_LANGS = {"en", "fr"}
# Load model once
MODEL = SentenceTransformer("all-MiniLM-L6-v2")

def clean_value(value_dict: dict) -> str | None:
    """
    Takes a SPARQL binding object and returns a clean string.
    Forcefully strips URLs to just the last part.
    """
    if not value_dict:
        return None
        
    raw_val = value_dict.get("value", "").strip()
    if not raw_val:
        return None

    # 1. Handle URI: Keep ONLY text after the last slash
    if value_dict.get("type") == "uri" or raw_val.startswith("http"):
        # split by / and take the last part
        raw_val = raw_val.rsplit("/", 1)[-1]
        # split by # (common in RDF) and take last part
        raw_val = raw_val.rsplit("#", 1)[-1]
        # Optional: Replace underscores with spaces for readability
        raw_val = raw_val.replace("_", " ")

    # 2. Language filter (only for literals with lang tags)
    lang = value_dict.get("xml:lang")
    if lang and lang not in PREFERRED_LANGS:
        return None

    # 3. Skip pure numbers (usually internal IDs)
    if raw_val.isdigit():
        return None

    return raw_val

def row_to_clean_dict(row: dict) -> dict:
    """
    Converts a SPARQL row dictionary into a flat Python dict
    with clean values only.
    """
    clean_row = {}
    for col_name, cell_data in row.items():
        clean_val = clean_value(cell_data)
        if clean_val:
            clean_row[col_name] = clean_val
    return clean_row

def find_best_k(embeddings, min_k=3, max_k=10):
    """
    Determines optimal number of clusters. 
    Raised min_k to 3 to avoid the 'everything is one binary blob' issue.
    """
    n_rows = len(embeddings)
    if n_rows < min_k:
        return max(1, n_rows) # Fallback for tiny data
    
    max_k = min(max_k, n_rows - 1)
    
    best_k = min_k
    best_score = -1.0

    for k in range(min_k, max_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(embeddings)
        labels = km.labels_
        
        # Silhouette requires at least 2 distinct clusters
        if len(set(labels)) < 2: 
            continue
            
        score = silhouette_score(embeddings, labels)
        
        # We prefer a slightly higher k if the score is similar, to break up blobs
        if score > best_score:
            best_score = score
            best_k = k
            
    return best_k

def generate_cluster_name(df_cluster: pd.DataFrame) -> str:
    """
    Scans ALL columns in the cluster to find the most common descriptive feature.
    """
    # Exclude non-descriptive columns
    ignore = {"x", "y", "cluster", "cluster_name", "hover", "label", "name", "nom", "text_for_embedding"}
    
    # Collect all values from all relevant columns into a single list
    all_values = []
    for col in df_cluster.columns:
        if col in ignore:
            continue
        # add values to list, skipping None/NaN
        all_values.extend(df_cluster[col].dropna().astype(str).tolist())

    if not all_values:
        return "Misc"

    # Find the single most common value in this cluster
    # e.g. "Science Fiction" appears 50 times
    most_common = Counter(all_values).most_common(1)
    
    if most_common:
        return most_common[0][0] # Return the name of the feature
    return "Unknown"

def semantic_cluster_dbpedia(query_results: dict) -> pd.DataFrame:
    # 1. Extract and Clean Data
    raw_rows = query_results["results"]["bindings"]
    cleaned_rows = [row_to_clean_dict(row) for row in raw_rows]
    
    # Create DataFrame immediately
    df = pd.DataFrame(cleaned_rows)
    
    # 2. Create Embedding Text
    # We combine all values (except name/label) into one string for the AI
    def make_embedding_text(row_series):
        # Filter out names so we cluster by properties (genre, job, etc), not alphabetical
        values = [str(v) for k, v in row_series.items() 
                 if k.lower() not in ["label", "name", "nom"] and pd.notna(v)]
        return " ".join(values)

    df["text_for_embedding"] = df.apply(make_embedding_text, axis=1)
    
    # 3. Embed
    embeddings = MODEL.encode(
        df["text_for_embedding"].tolist(),
        normalize_embeddings=True,
        show_progress_bar=False
    )

    # 4. Cluster
    # If we have enough data, force at least 3 clusters, otherwise adapt
    k = find_best_k(embeddings, min_k=3, max_k=12)
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    df["cluster"] = km.fit_predict(embeddings)

    # 5. UMAP Reduction (Coordinates)
    reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, metric='cosine', random_state=42)
    coords = reducer.fit_transform(embeddings)
    df["x"] = coords[:, 0]
    df["y"] = coords[:, 1]

    # 6. Name Clusters
    # We group the dataframe by cluster ID and ask the naming function to find the pattern
    cluster_names = {}
    for c_id in df["cluster"].unique():
        cluster_names[c_id] = generate_cluster_name(df[df["cluster"] == c_id])
    
    df["cluster_name"] = df["cluster"].map(cluster_names)

    # 7. Prepare Hover
    df["hover"] = df.apply(prepare_hover, axis=1)
    
    return df

def prepare_hover(row):
    """Creates clean HTML for hover."""
    lines = []
    
    # Try to find a title/label first
    title = row.get("label") or row.get("name") or row.get("nom")
    if title:
        lines.append(f"<b>{title}</b>")
    
    # Add other properties
    exclude = {"x", "y", "cluster", "cluster_name", "hover", "text_for_embedding", "label", "name", "nom"}
    for k, v in row.items():
        if k not in exclude and pd.notna(v):
            lines.append(f"{k}: {v}")
            
    return "<br>".join(lines)

def plot_clusters(df: pd.DataFrame):
    fig = px.scatter(
        df,
        x="x",
        y="y",
        color="cluster_name",
        hover_data={"hover": True, "x": False, "y": False, "cluster_name": False}
    )

    fig.update_traces(
        marker=dict(size=10, opacity=0.8),
        hovertemplate="%{customdata[0]}<extra></extra>"
    )
    
    fig.update_layout(
        legend_title_text="Cluster",
        margin=dict(l=10, r=10, t=30, b=10)
        # Removed 'plot_bgcolor="white"' to keep default look
    )
    
    return fig

'''


def find_k(embeddings: ndarray, min_k: int = 2, max_k: int = 6) -> int:
    """Find the optimal number of clusters (k) using the silhouette score method.
    Args:
        embeddings (numpy.ndarray): The embeddings to cluster.
        min_k (int, optional): Minimum number of clusters to try. Defaults to 2.
        max_k (int, optional): Maximum number of clusters to try. Defaults to 6.
    Returns:
        int: The optimal number of clusters.
    """
    assert min_k >= 2, "min_k must be at least 2"
    assert max_k >= min_k, "max_k must be greater than or equal to min_k"

    best_k = 2
    best_score = -1

    for k in range(min_k, max_k + 1):
        km = KMeans(n_clusters=k)
        labels = km.fit_predict(embeddings)
        score = silhouette_score(embeddings, labels)
        if score > best_score:  # silhouette_score is better when higher, belogs to [-1, 1]
            best_score = score
            best_k = k

    return best_k


def cluster_embeddings_KMeans(query_results: dict, min_k: int = 2, max_k: int = 6) -> pd.DataFrame:
    """Cluster the embeddings of the query results using KMeans.
    Args:
        query_results (dict): The results of the SPARQL query.
        min_k (int, optional): Minimum number of clusters to try. Defaults to 2.
        max_k (int, optional): Maximum number of clusters to try. Defaults to 6.
    Returns:
        pd.DataFrame: A DataFrame with the original data, embeddings, and cluster labels.
    """
    data = []
    for row in query_results["results"]["bindings"]:
        data.append({k: v["value"] for k, v in row.items()})

    df = pd.DataFrame(data)
    if df.empty:
        raise ValueError("The query results are empty, cannot perform clustering.")

    df["text_for_embedding"] = df.apply(lambda row: " ".join(row.values.astype(str)), axis=1)

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(df["text_for_embedding"].tolist())
    print(type(embeddings))
    df["embedding"] = embeddings.tolist()

    n_clusters = find_k(embeddings, min_k=min_k, max_k=max_k) if len(df) >= 2 else 1

    kmeans = KMeans(n_clusters=n_clusters)
    df["cluster"] = kmeans.fit_predict(embeddings).astype(str)
    return df


VALUE_COL_NAMES = ["value", "label", "name", "nom", "artiste", "valeur", "artist", "album"]




    
    
'''