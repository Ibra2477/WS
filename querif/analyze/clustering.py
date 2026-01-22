import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from plotly.graph_objs._figure import Figure
import plotly.express as px
from sklearn.metrics import silhouette_score
from numpy import ndarray


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


def plot_clusters(df: pd.DataFrame) -> Figure:
    """Plot the clusters of the embeddings in 2D using PCA.
    Args:
        df (pd.DataFrame): The DataFrame with the original data, embeddings, and cluster labels.
    Returns:
        plotly.graph_objs._figure.Figure: The plotly figure object.
    """
    pca = PCA(n_components=2)
    coords = pca.fit_transform(df["embedding"].tolist())
    df["pc_1"], df["pc_2"] = coords[:, 0], coords[:, 1]

    # On essaie de trouver une colonne "nom" ou "label" pour l'affichage
    col_namees = [c for c in df.columns if c.lower() in VALUE_COL_NAMES]
    display_name = col_namees[0] if col_namees else df.columns[0]

    fig = px.scatter(
        df,
        x="pc_1",
        y="pc_2",
        color="cluster",
        text=display_name,  # Affiche le nom sur le point
        hover_data=df.columns.drop(["pc_1", "pc_2", "text_for_embedding"]),
        title="Semantoc Analysis: Clustering Visualization",
        template="plotly_dark",
    )
    fig.update_traces(textposition="top center")  # Ajustement de la position du texte pour qu'il ne soit pas sur le point
    return fig
