import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import plotly.express as px
from sklearn.metrics import silhouette_score


def find_k(embeddings, min_k=2, max_k=6):
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


def cluster_embeddings_KMeans(query_results: dict):
    data = []
    for row in query_results["results"]["bindings"]:
        data.append({k: v["value"] for k, v in row.items()})

    df = pd.DataFrame(data)
    if df.empty:
        return "No data", None

    df["text_for_embedding"] = df.apply(lambda row: " ".join(row.values.astype(str)), axis=1)

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(df["text_for_embedding"].tolist())
    df["embedding"] = embeddings.tolist()

    n_clusters = find_k(embeddings) if len(df) >= 2 else 1

    kmeans = KMeans(n_clusters=n_clusters)
    df["cluster"] = kmeans.fit_predict(embeddings).astype(str)
    return df


VALUE_COL_NAMES = ["value", "label", "name", "nom", "artiste", "valeur", "artist", "album"]


def plot_clusters(df: pd.DataFrame):
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
