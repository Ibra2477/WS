import networkx as nx
import matplotlib.pyplot as plt
from enum import Enum
from typing import Optional, List, Dict, Tuple

class QueryType(Enum):
    """Types de requêtes supportés par le système NL2SPARQL"""
    FACT_LOOKUP = "FACT_LOOKUP"
    CLASS_QUERY = "CLASS_QUERY"
    AGGREGATION = "AGGREGATION"
    COMPARISON = "COMPARISON"
    DEFINITION = "DEFINITION"
    RELATIONSHIP = "RELATIONSHIP"
    SUPERLATIVE = "SUPERLATIVE"
    BOOLEAN = "BOOLEAN"

class GraphDB:
    """Base de données en graphe pour représenter les requêtes SPARQL et leurs relations"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.query_types = {}  # Mappe query_id -> QueryType
        self.query_content = {}  # Mappe query_id -> contenu de la requête
        self.sparql_queries = {}  # Mappe query_id -> requête SPARQL
        
        # Couleurs pour chaque type de requête
        self.type_colors = {
            QueryType.FACT_LOOKUP: '#FF6B6B',
            QueryType.CLASS_QUERY: '#4ECDC4',
            QueryType.AGGREGATION: '#45B7D1',
            QueryType.COMPARISON: '#FFA07A',
            QueryType.DEFINITION: '#98D8C8',
            QueryType.RELATIONSHIP: '#F7DC6F',
            QueryType.SUPERLATIVE: '#BB8FCE',
            QueryType.BOOLEAN: '#85C1E2',
        }

    def add_query(self, query_id: str, natural_language: str, query_type: QueryType, sparql: Optional[str] = None):
        """Ajoute une requête au graphe"""
        self.graph.add_node(query_id, type=query_type.value)
        self.query_types[query_id] = query_type
        self.query_content[query_id] = natural_language
        if sparql:
            self.sparql_queries[query_id] = sparql

    def add_relation(self, from_query_id: str, to_query_id: str, relation_type: str = "depends_on"):
        """Ajoute une relation dirigée entre deux requêtes"""
        self.graph.add_edge(from_query_id, to_query_id, relation=relation_type)

    def get_graph(self):
        """Retourne le graphe NetworkX"""
        return self.graph

    def get_query_info(self, query_id: str) -> Dict:
        """Retourne les informations d'une requête"""
        return {
            'id': query_id,
            'type': self.query_types.get(query_id).value if query_id in self.query_types else None,
            'natural_language': self.query_content.get(query_id),
            'sparql': self.sparql_queries.get(query_id),
        }

    def display_graph(self) -> Dict:
        """Affiche le graphe sous forme de liste d'adjacence"""
        return nx.to_dict_of_lists(self.graph)

    def get_queries_by_type(self, query_type: QueryType) -> List[str]:
        """Retourne toutes les requêtes d'un type donné"""
        return [q_id for q_id, q_type in self.query_types.items() if q_type == query_type]

    def get_dependencies(self, query_id: str) -> List[str]:
        """Retourne les dépendances d'une requête (requêtes dont elle dépend)"""
        return list(self.graph.predecessors(query_id))

    def get_dependents(self, query_id: str) -> List[str]:
        """Retourne les requêtes qui dépendent de cette requête"""
        return list(self.graph.successors(query_id))

    def visualize(self, filename: Optional[str] = None, show_sparql: bool = False):
        """Visualise le graphe avec coloration par type de requête"""
        if len(self.graph.nodes()) == 0:
            print("Le graphe est vide. Ajoutez des requêtes d'abord.")
            return

        plt.figure(figsize=(14, 10))
        pos = nx.spring_layout(self.graph, k=2.5, iterations=50, seed=42)
        
        # Couleurs des nœuds selon le type
        node_colors = [self.type_colors.get(self.query_types.get(node), '#CCCCCC') for node in self.graph.nodes()]
        
        # Dessine les nœuds
        nx.draw_networkx_nodes(self.graph, pos, node_color=node_colors, node_size=2000, alpha=0.9)
        
        # Dessine les arêtes
        nx.draw_networkx_edges(self.graph, pos, edge_color='gray', arrows=True, 
                              arrowsize=20, arrowstyle='->', width=2, alpha=0.6)
        
        # Dessine les labels
        labels = {node: node for node in self.graph.nodes()}
        nx.draw_networkx_labels(self.graph, pos, labels, font_size=9, font_weight='bold')
        
        # Légende des types
        legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                     markerfacecolor=color, markersize=10, label=query_type.value)
                          for query_type, color in self.type_colors.items()]
        plt.legend(handles=legend_elements, loc='upper left', fontsize=10)
        
        plt.title("Graphe des Requêtes SPARQL", fontsize=16, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        
        if filename:
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Graphe sauvegardé dans {filename}")
        else:
            plt.show()

    def print_summary(self):
        """Affiche un résumé du graphe"""
        print("=" * 60)
        print("RÉSUMÉ DU GRAPHE DES REQUÊTES")
        print("=" * 60)
        print(f"Nombre total de requêtes: {len(self.graph.nodes())}")
        print(f"Nombre de relations: {len(self.graph.edges())}")
        print()
        
        # Compte par type
        type_counts = {}
        for query_type in QueryType:
            count = len(self.get_queries_by_type(query_type))
            if count > 0:
                type_counts[query_type] = count
        
        print("Requêtes par type:")
        for query_type, count in type_counts.items():
            print(f"  {query_type.value}: {count}")
        print()
        
        # Détails des requêtes
        print("Détails des requêtes:")
        for query_id in sorted(self.graph.nodes()):
            info = self.get_query_info(query_id)
            deps = self.get_dependencies(query_id)
            print(f"\n  [{query_id}] Type: {info['type']}")
            print(f"    Question: {info['natural_language']}")
            if info['sparql']:
                print(f"    SPARQL: {info['sparql'][:80]}...")
            if deps:
                print(f"    Dépend de: {', '.join(deps)}")