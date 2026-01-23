import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
import plotly.express as px
from sklearn.metrics import silhouette_score
from collections import Counter
import umap.umap_ as umap
from numpy import ndarray

# --- CONFIGURATION ---
PREFERRED_LANGS = {"en", "fr"}
MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def clean_value(value_dict: dict) -> str | None:
    """
    Cleans SPARQL values.
    Crucially, it handles AGGLOMERATED lists (comma-separated URIs)
    by splitting them first, cleaning each, and re-joining.
    Args:
        value_dict (dict): A SPARQL value dictionary.
    Returns:
        str | None: The cleaned value or None if invalid.
    """
    if not value_dict:
        return None

    raw_val = value_dict.get("value", "").strip()
    if not raw_val:
        return None

    # Handle Agglomerated Lists (e.g. "http://.../A, http://.../B")
    # We check if it looks like a list of links
    if "," in raw_val and "http" in raw_val:
        parts = raw_val.split(",")
        cleaned_parts = []
        for p in parts:
            p = p.strip()
            # Clean each part individually
            if "/" in p:
                p = p.rsplit("/", 1)[-1]
            if "#" in p:
                p = p.rsplit("#", 1)[-1]
            p = p.replace("_", " ")
            cleaned_parts.append(p)
        return ", ".join(cleaned_parts)

    # Handle Single URI
    if value_dict.get("type") == "uri" or raw_val.startswith("http"):
        raw_val = raw_val.rsplit("/", 1)[-1]
        raw_val = raw_val.rsplit("#", 1)[-1]
        raw_val = raw_val.replace("_", " ")

    # Handle Language Tags
    lang = value_dict.get("xml:lang")
    if lang and lang not in PREFERRED_LANGS:
        return None

    # Skip pure numbers
    if raw_val.isdigit():
        return None

    return raw_val


def row_to_clean_dict(row: dict) -> dict:
    """Cleans a SPARQL result row into a simple dict.
    Args:
        row (dict): A SPARQL result row.
    Returns:
        dict: A cleaned dictionary with column names and cleaned values.
    """
    clean_row = {}
    for col_name, cell_data in row.items():
        clean_val = clean_value(cell_data)
        if clean_val:
            clean_row[col_name] = clean_val
    return clean_row


def find_best_k(embeddings: ndarray, min_k: int = 3, max_k: int = 12) -> int:
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

    n_rows = len(embeddings)
    if n_rows < min_k:
        return max(1, n_rows)

    max_k = min(max_k, n_rows - 1)
    best_k = min_k
    best_score = -1.0

    for k in range(min_k, max_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(embeddings)
        labels = km.labels_

        if len(set(labels)) < 2:
            continue

        score = silhouette_score(embeddings, labels)
        if score > best_score:
            best_score = score
            best_k = k

    return best_k


def generate_cluster_name(df_cluster: pd.DataFrame, top_n: int = 2) -> str:
    """
    Scans all columns to find the top shared attributes.
    Splits agglomerated strings (comma-separated) to count individual tags.
    Args:
        df_cluster (pd.DataFrame): DataFrame of the cluster.
        top_n (int, optional): Number of top tokens to include in the name. Defaults to 2.
    Returns:
        str: Generated cluster name.
    """
    ignore = {"x", "y", "cluster", "cluster_name", "hover", "label", "name", "nom", "text_for_embedding"}

    all_tokens = []

    for col in df_cluster.columns:
        if col in ignore:
            continue

        # Get all text values in this column
        raw_values = df_cluster[col].dropna().astype(str).tolist()

        for val in raw_values:
            # If the cell is "Action, Sci-Fi", split it so we count them separately
            tokens = val.split(",")
            for t in tokens:
                t = t.strip()
                if t:
                    all_tokens.append(t)

    if not all_tokens:
        return "Group " + str(len(df_cluster))

    # Count most frequent tokens
    counts = Counter(all_tokens)
    most_common = counts.most_common(top_n)

    # Create name like "Writer | French | Novelist"
    name_parts = [token for token, count in most_common]
    return " | ".join(name_parts)


def semantic_cluster_dbpedia(query_results: dict) -> pd.DataFrame:
    """Performs semantic clustering on SPARQL query results from DBpedia.
    Args:
        query_results (dict): The results of the SPARQL query.
    Returns:
        pd.DataFrame: A DataFrame with clustering results and coordinates for visualization.
    """
    raw_rows = query_results["results"]["bindings"]

    # 1. Clean Data (Fixes the URL cutting issue)
    cleaned_rows = [row_to_clean_dict(row) for row in raw_rows]
    df = pd.DataFrame(cleaned_rows)

    # 2. Embedding Text
    def make_embedding_text(row_series):
        # We join all properties for the AI
        values = [str(v) for k, v in row_series.items() if k.lower() not in ["label", "name", "nom"] and pd.notna(v)]
        return " ".join(values)

    df["text_for_embedding"] = df.apply(make_embedding_text, axis=1)

    # 3. Cluster
    embeddings = MODEL.encode(df["text_for_embedding"].tolist(), show_progress_bar=False)
    k = find_best_k(embeddings, min_k=3, max_k=15)  # Force check up to 15 clusters
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    df["cluster"] = km.fit_predict(embeddings)

    # 4. Reduce Dimensions
    reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, metric="cosine", random_state=42)
    coords = reducer.fit_transform(embeddings)
    df["x"] = coords[:, 0]
    df["y"] = coords[:, 1]

    # 5. Name Clusters (Multi-word names)
    cluster_names = {}
    for c_id in df["cluster"].unique():
        cluster_names[c_id] = generate_cluster_name(df[df["cluster"] == c_id])
    df["cluster_name"] = df["cluster"].map(cluster_names)

    # 6. Prepare Hover
    df["hover"] = df.apply(prepare_hover, axis=1)

    return df


def prepare_hover(row):
    lines = []
    # Header
    title = row.get("label") or row.get("name") or row.get("nom")
    if title:
        lines.append(f"<b>{title}</b>")

    # Body
    exclude = {"x", "y", "cluster", "cluster_name", "hover", "text_for_embedding", "label", "name", "nom"}
    for k, v in row.items():
        if k not in exclude and pd.notna(v):
            # v is now "Action, Comedy" correctly
            lines.append(f"{k.capitalize()}: {v}")

    return "<br>".join(lines)


def plot_clusters(df: pd.DataFrame):
    fig = px.scatter(df, x="x", y="y", color="cluster_name", hover_data={"hover": True, "x": False, "y": False, "cluster_name": False})
    fig.update_traces(marker=dict(size=10, opacity=0.8), hovertemplate="%{customdata[0]}<extra></extra>")
    fig.update_layout(legend_title_text="Cluster", margin=dict(l=10, r=10, t=30, b=10))
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
