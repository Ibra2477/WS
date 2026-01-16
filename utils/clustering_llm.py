import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import plotly.express as px


def analyse_universelle(resultats_json):
    data = []
    for row in resultats_json['results']['bindings']:
        data.append({k: v['value'] for k, v in row.items()})
    
    df = pd.DataFrame(data)
    if df.empty: return "Aucune donnée", None

    # Correction .values (sans parenthèses)
    df['text_for_embedding'] = df.apply(lambda row: " ".join(row.values.astype(str)), axis=1)

    # Embeddings
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(df['text_for_embedding'].tolist())

    # Clustering
    n_clusters = min(4, len(df))
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    df['cluster'] = kmeans.fit_predict(embeddings).astype(str)

    # PCA
    pca = PCA(n_components=2)
    coords = pca.fit_transform(embeddings)
    df['x'], df['y'] = coords[:, 0], coords[:, 1]

    # --- AMÉLIORATION DE LA VISUALISATION ---
    # On essaie de trouver une colonne "nom" ou "label" pour l'affichage
    colonnes_nom = [c for c in df.columns if c.lower() in ['name', 'label', 'artiste', 'nom']]
    nom_affichage = colonnes_nom[0] if colonnes_nom else df.columns[0]

    fig = px.scatter(
        df, x='x', y='y', 
        color='cluster',
        text=nom_affichage, # Affiche le nom sur le point
        hover_data=df.columns.drop(['x', 'y', 'text_for_embedding']),
        title="Analyse Sémantique : Regroupement par proximité de profil",
        template='plotly_dark'
    )

    # Ajustement de la position du texte pour qu'il ne soit pas sur le point
    fig.update_traces(textposition='top center')
    
    return df, fig