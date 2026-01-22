import networkx as nx
import plotly.graph_objects as go
from typing import Dict, List, Tuple


def build_graph_from_results(results: dict, source_key: str, target_key: str) -> nx.Graph:
    """Construit un graphe simple à partir des résultats SPARQL.
    
    Args:
        results: Résultats SPARQL (dict avec 'results'/'bindings')
        source_key: Clé pour le nœud source (ex: 'songLabel')
        target_key: Clé pour le nœud cible (ex: 'writers')
    
    Returns:
        Un graphe NetworkX
    """
    G = nx.Graph()
    
    for binding in results['results']['bindings']:
        if source_key in binding and target_key in binding:
            source = binding[source_key]['value']
            target_value = binding[target_key]['value']
            
            # Si target contient plusieurs valeurs séparées par " | ", les séparer
            if ' | ' in target_value:
                targets = [t.strip() for t in target_value.split(' | ')]
                for target in targets:
                    G.add_edge(source, target)
            else:
                G.add_edge(source, target_value)
    
    return G


def calculate_metrics(G: nx.Graph) -> dict:
    """Calcule les métriques de centralité du graphe.
    
    Args:
        G: Graphe NetworkX
    
    Returns:
        Dict avec les métriques pour chaque nœud
    """
    metrics = {
        'degree': dict(G.degree()),
        'pagerank': nx.pagerank(G),
        'betweenness': nx.betweenness_centrality(G),
    }
    
    # Détection de communautés
    try:
        communities = nx.community.greedy_modularity_communities(G)
        node_to_community = {}
        for i, community in enumerate(communities):
            for node in community:
                node_to_community[node] = i
        metrics['community'] = node_to_community
    except:
        metrics['community'] = {node: 0 for node in G.nodes()}
    
    return metrics


def plot_graph(G: nx.Graph, metrics: dict = None, title: str = "Network Graph") -> go.Figure:
    """Visualise le graphe avec Plotly.
    
    Args:
        G: Graphe NetworkX
        metrics: Métriques calculées (optionnel)
        title: Titre du graphe
    
    Returns:
        Figure Plotly
    """
    # Position des nœuds
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    
    # Créer les arêtes
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Créer les nœuds
    node_x = []
    node_y = []
    node_text = []
    node_size = []
    node_color = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        # Nom court pour affichage
        node_name = node.split('/')[-1].replace('_', ' ')
        node_text.append(node_name)
        
        # Taille selon le degré
        if metrics and 'degree' in metrics:
            node_size.append(10 + metrics['degree'][node] * 5)
        else:
            node_size.append(20)
        
        # Couleur selon la communauté
        if metrics and 'community' in metrics:
            node_color.append(metrics['community'][node])
        else:
            node_color.append(0)
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        marker=dict(
            size=node_size,
            color=node_color,
            colorscale='Viridis',
            line=dict(width=2, color='white')
        ),
        hoverinfo='text'
    )
    
    # Créer la figure
    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title=title,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        height=600
                    ))
    
    return fig


def get_top_nodes(metrics: dict, metric_name: str, top_n: int = 5) -> List[Tuple[str, float]]:
    """Retourne les top N nœuds pour une métrique donnée.
    
    Args:
        metrics: Dict des métriques
        metric_name: Nom de la métrique ('degree', 'pagerank', 'betweenness')
        top_n: Nombre de résultats
    
    Returns:
        Liste de tuples (nœud, valeur)
    """
    if metric_name not in metrics:
        return []
    
    sorted_nodes = sorted(metrics[metric_name].items(), key=lambda x: x[1], reverse=True)
    
    # Nettoyer les noms pour affichage
    result = []
    for node, value in sorted_nodes[:top_n]:
        clean_name = node.split('/')[-1].replace('_', ' ')
        result.append((clean_name, value))
    
    return result


def export_to_gephi(G: nx.Graph, filepath: str):
    """Exporte le graphe au format GEXF pour Gephi.
    
    Args:
        G: Graphe NetworkX
        filepath: Chemin du fichier de sortie (.gexf)
    """
    nx.write_gexf(G, filepath)
    print(f"Graphe exporté vers {filepath}")


def analyze_graph(results: dict, source_key: str, target_key: str, title: str = "Network Graph"):
    """Fonction tout-en-un : construit, analyse et visualise le graphe.
    
    Args:
        results: Résultats SPARQL
        source_key: Clé pour le nœud source
        target_key: Clé pour le nœud cible
        title: Titre du graphe
    
    Returns:
        Tuple (graphe, métriques, figure)
    """
    G = build_graph_from_results(results, source_key, target_key)
    metrics = calculate_metrics(G)
    fig = plot_graph(G, metrics, title)
    
    # Afficher les stats
    print(f"Nombre de nœuds: {G.number_of_nodes()}")
    print(f"Nombre d'arêtes: {G.number_of_edges()}")
    print(f"\nTop 5 par degré:")
    for name, value in get_top_nodes(metrics, 'degree', 5):
        print(f"  {name}: {value}")
    
    print(f"\nTop 5 PageRank:")
    for name, value in get_top_nodes(metrics, 'pagerank', 5):
        print(f"  {name}: {value:.4f}")
    
    return G, metrics, fig
