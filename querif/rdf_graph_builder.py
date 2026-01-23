"""
RDF Graph Builder - Construit un graphe RDF Ã  partir d'une requÃªte SPARQL
"""
import re
import networkx as nx
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Tuple, Optional, Set
from .const.prefixes import namespaces, uri_to_prefixed, prefixed_to_uri


class RDFGraphBuilder:
    """Construit et visualise un graphe RDF Ã  partir d'une requÃªte SPARQL"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.entities = {}  # Mappe entity_id -> {type, label, uri}
        self.properties = []  # Liste des propriÃ©tÃ©s (sujet, prÃ©dicat, objet)
        
        # Couleurs pour diffÃ©rents types de nÅ“uds
        self.node_colors = {
            'resource': '#FF6B6B',  # Rouge pour les ressources/entitÃ©s
            'class': '#4ECDC4',     # Cyan pour les classes
            'literal': '#98D8C8',   # Vert clair pour les littÃ©raux
            'property': '#FFA07A',  # Orange pour les propriÃ©tÃ©s
        }
    
    def parse_sparql_query(self, sparql_query: str) -> Dict:
        """
        Analyse une requÃªte SPARQL pour extraire les entitÃ©s, classes et propriÃ©tÃ©s
        
        Args:
            sparql_query: RequÃªte SPARQL Ã  analyser
            
        Returns:
            Dict contenant les entitÃ©s, classes et relations extraites
        """
        result = {
            'main_entity': None,
            'classes': [],
            'properties': [],
            'filters': []
        }
        
        # Extraire les clauses WHERE
        where_match = re.search(r'WHERE\s*\{(.*?)\}', sparql_query, re.DOTALL | re.IGNORECASE)
        if not where_match:
            return result
        
        where_clause = where_match.group(1)
        
        # Extraire les triples (sujet prÃ©dicat objet)
        triple_pattern = r'\??\w+\s+([a-zA-Z_:]+)\s+(\??\w+|<[^>]+>|"[^"]*")'
        triples = re.findall(triple_pattern, where_clause)
        
        # Extraire rdf:type pour identifier les classes
        type_pattern = r'(\?\w+)\s+(rdf:type|a)\s+([a-zA-Z_:]+)'
        type_matches = re.findall(type_pattern, where_clause, re.IGNORECASE)
        
        for var, _, class_type in type_matches:
            result['classes'].append({
                'variable': var,
                'class': class_type
            })
        
        # Extraire les propriÃ©tÃ©s
        property_pattern = r'(\?\w+|<[^>]+>|[a-zA-Z_:]+)\s+([a-zA-Z_:]+)\s+(\?\w+|<[^>]+>|"[^"]*")'
        property_matches = re.findall(property_pattern, where_clause)
        
        for subj, pred, obj in property_matches:
            if pred not in ['rdf:type', 'a']:
                result['properties'].append({
                    'subject': subj,
                    'predicate': pred,
                    'object': obj
                })
        
        # Identifier l'entitÃ© principale (resource nommÃ©e)
        resource_pattern = r'(dbr:[A-Za-z_0-9]+)'
        resources = re.findall(resource_pattern, sparql_query)
        if resources:
            result['main_entity'] = resources[0]
        
        return result
    
    def build_from_sparql(self, sparql_query: str, natural_language: str = ""):
        """
        Construit le graphe RDF Ã  partir d'une requÃªte SPARQL
        
        Args:
            sparql_query: RequÃªte SPARQL
            natural_language: Question en langage naturel (optionnel)
        """
        parsed = self.parse_sparql_query(sparql_query)
        
        # Ajouter les classes comme nÅ“uds
        for class_info in parsed['classes']:
            var = class_info['variable']
            class_type = class_info['class']
            
            # Ajouter la classe comme nÅ“ud de type
            self.add_entity(class_type, 'class', class_type.split(':')[-1])
            
            # Ajouter la variable comme instance de cette classe
            self.add_entity(var, 'resource', var)
            self.add_property(var, 'rdf:type', class_type)
        
        # Ajouter l'entitÃ© principale
        if parsed['main_entity']:
            entity = parsed['main_entity']
            entity_name = entity.split(':')[-1].replace('_', ' ')
            self.add_entity(entity, 'resource', entity_name)
        
        # Ajouter les propriÃ©tÃ©s et relations
        for prop in parsed['properties']:
            subj = prop['subject']
            pred = prop['predicate']
            obj = prop['object']
            
            # DÃ©terminer le type de l'objet
            if obj.startswith('?'):
                obj_type = 'resource'
            elif obj.startswith('"'):
                obj_type = 'literal'
                obj = obj.strip('"')
            else:
                obj_type = 'resource'
            
            # Ajouter les entitÃ©s si elles n'existent pas
            if subj not in self.entities:
                self.add_entity(subj, 'resource', subj)
            if obj not in self.entities:
                self.add_entity(obj, obj_type, obj)
            
            # Ajouter la propriÃ©tÃ©
            self.add_property(subj, pred, obj)
    
    def build_from_results(self, sparql_query: str, results: dict, max_results: int = 20):
        """
        Construit le graphe RDF Ã  partir des rÃ©sultats rÃ©els d'une requÃªte SPARQL
        
        Args:
            sparql_query: RequÃªte SPARQL originale
            results: RÃ©sultats de l'exÃ©cution de la requÃªte (format SPARQLWrapper JSON)
            max_results: Nombre maximum de rÃ©sultats Ã  inclure dans le graphe
        """
        if not results or 'results' not in results or 'bindings' not in results['results']:
            print("Aucun rÃ©sultat Ã  traiter")
            return
        
        bindings = results['results']['bindings'][:max_results]
        
        # Extraire l'entitÃ© principale et la classe de la requÃªte
        parsed = self.parse_sparql_query(sparql_query)
        main_class = None
        main_entity = parsed.get('main_entity')
        
        # DÃ©tecter l'entitÃ© principale depuis l'URI complÃ¨te si prÃ©sente
        artist_match = re.search(r'<http://dbpedia\.org/resource/([^>]+)>', sparql_query)
        if artist_match and not main_entity:
            main_entity = f"dbr:{artist_match.group(1)}"
        
        if parsed['classes']:
            main_class = parsed['classes'][0]['class']
        
        # Ajouter l'entitÃ© principale (ex: Drake)
        if main_entity:
            entity_name = main_entity.split(':')[-1].replace('_', ' ').replace('(musician)', '').strip()
            self.add_entity(main_entity, 'resource', entity_name, main_entity)
        
        # Ajouter la classe principale
        if main_class:
            class_name = main_class.split(':')[-1]
            self.add_entity(main_class, 'class', class_name)
        
        # Traiter chaque rÃ©sultat
        for idx, binding in enumerate(bindings):
            result_id = f"result_{idx}"
            
            # Pour chaque variable dans les rÃ©sultats
            for var_name, var_value in binding.items():
                value_type = var_value.get('type')
                value = var_value.get('value')
                
                if not value:
                    continue
                
                # CrÃ©er un ID unique pour cette ressource
                if value_type == 'uri':
                    # Convertir l'URI en format prÃ©fixÃ©
                    resource_id = uri_to_prefixed(value)
                    if resource_id == value:  # Si pas de prÃ©fixe trouvÃ©
                        resource_id = value.split('/')[-1]
                    
                    # Extraire un label lisible
                    label = resource_id.split(':')[-1].replace('_', ' ')
                    
                    # DÃ©terminer le type selon la variable
                    if var_name in ['album', 'movie', 'film', 'book', 'song']:
                        node_type = 'resource'
                        # Ajouter l'instance
                        self.add_entity(resource_id, node_type, label, value)
                        
                        # Lier Ã  la classe
                        if main_class:
                            self.add_property(resource_id, 'rdf:type', main_class)
                        
                        # Lier Ã  l'entitÃ© principale
                        if main_entity:
                            # DÃ©tecter le type de relation
                            if 'artist' in sparql_query.lower():
                                self.add_property(resource_id, 'dbo:artist', main_entity)
                            elif 'director' in sparql_query.lower():
                                self.add_property(resource_id, 'dbo:director', main_entity)
                            elif 'author' in sparql_query.lower():
                                self.add_property(resource_id, 'dbo:author', main_entity)
                    else:
                        self.add_entity(resource_id, 'resource', label, value)
                
                elif value_type == 'literal':
                    # C'est un littÃ©ral (titre, label, etc.)
                    literal_id = f"literal_{idx}_{var_name}"
                    
                    # Tronquer si trop long
                    display_value = value[:50] + "..." if len(value) > 50 else value
                    
                    self.add_entity(literal_id, 'literal', display_value)
                    
                    # Trouver la ressource associÃ©e et crÃ©er le lien
                    # La ressource est souvent dans la variable prÃ©cÃ©dente
                    if 'album' in binding:
                        album_uri = binding['album']['value']
                        album_id = uri_to_prefixed(album_uri)
                        if album_id == album_uri:
                            album_id = album_uri.split('/')[-1]
                        
                        # DÃ©terminer la propriÃ©tÃ© (title, label, name)
                        if var_name in ['title', 'label', 'name']:
                            self.add_property(album_id, f'rdfs:{var_name}', literal_id)
                    elif 'song' in binding:
                        song_uri = binding['song']['value']
                        song_id = uri_to_prefixed(song_uri)
                        if song_id == song_uri:
                            song_id = song_uri.split('/')[-1]
                        
                        if var_name in ['title', 'label', 'name']:
                            self.add_property(song_id, f'rdfs:{var_name}', literal_id)
                    elif 'movie' in binding or 'film' in binding:
                        resource_key = 'movie' if 'movie' in binding else 'film'
                        resource_uri = binding[resource_key]['value']
                        resource_id = uri_to_prefixed(resource_uri)
                        if resource_id == resource_uri:
                            resource_id = resource_uri.split('/')[-1]
                        
                        if var_name in ['title', 'label', 'name']:
                            self.add_property(resource_id, f'rdfs:{var_name}', literal_id)
    
    def add_entity(self, entity_id: str, entity_type: str, label: str, uri: Optional[str] = None):
        """
        Ajoute une entitÃ© au graphe
        
        Args:
            entity_id: Identifiant unique de l'entitÃ©
            entity_type: Type de l'entitÃ© (resource, class, literal)
            label: Label lisible de l'entitÃ©
            uri: URI complÃ¨te (optionnel)
        """
        self.graph.add_node(entity_id, type=entity_type, label=label)
        self.entities[entity_id] = {
            'type': entity_type,
            'label': label,
            'uri': uri or entity_id
        }
    
    def add_property(self, subject: str, predicate: str, obj: str):
        """
        Ajoute une propriÃ©tÃ© (triple RDF) au graphe
        
        Args:
            subject: Sujet du triple
            predicate: PrÃ©dicat (propriÃ©tÃ©)
            obj: Objet du triple
        """
        self.graph.add_edge(subject, obj, property=predicate)
        self.properties.append((subject, predicate, obj))
    
    def visualize(self, filename: Optional[str] = None, title: str = "Graphe RDF"):
        """
        Visualise le graphe RDF
        
        Args:
            filename: Nom du fichier pour sauvegarder (None pour afficher)
            title: Titre du graphe
        """
        if len(self.graph.nodes()) == 0:
            print("Le graphe est vide.")
            return
        
        plt.figure(figsize=(16, 12))
        
        # Layout hiÃ©rarchique
        pos = nx.spring_layout(self.graph, k=3, iterations=50, seed=42)
        
        # SÃ©parer les nÅ“uds par type pour la coloration
        node_colors = []
        node_sizes = []
        for node in self.graph.nodes():
            node_type = self.entities.get(node, {}).get('type', 'resource')
            node_colors.append(self.node_colors.get(node_type, '#CCCCCC'))
            # Classes et ressources principales plus grandes
            if node_type == 'class':
                node_sizes.append(3000)
            elif node_type == 'resource':
                node_sizes.append(2500)
            else:
                node_sizes.append(1500)
        
        # Dessiner les nÅ“uds
        nx.draw_networkx_nodes(
            self.graph, pos,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=0.9,
            linewidths=2,
            edgecolors='black'
        )
        
        # Dessiner les arÃªtes
        nx.draw_networkx_edges(
            self.graph, pos,
            edge_color='#333333',
            arrows=True,
            arrowsize=30,
            arrowstyle='-|>',
            width=2.5,
            alpha=0.7,
            connectionstyle='arc3,rad=0.1',
            min_source_margin=25,
            min_target_margin=25
        )
        
        # Labels des nÅ“uds
        labels = {}
        for node in self.graph.nodes():
            entity = self.entities.get(node, {})
            label = entity.get('label', node)
            # Simplifier les labels trop longs
            if label.startswith('?'):
                labels[node] = label
            else:
                labels[node] = label.split(':')[-1].replace('_', ' ')[:20]
        
        nx.draw_networkx_labels(
            self.graph, pos,
            labels,
            font_size=10,
            font_weight='bold',
            font_color='black'
        )
        
        # Labels des arÃªtes (propriÃ©tÃ©s)
        edge_labels = {}
        for u, v, data in self.graph.edges(data=True):
            prop = data.get('property', '')
            edge_labels[(u, v)] = prop.split(':')[-1]
        
        nx.draw_networkx_edge_labels(
            self.graph, pos,
            edge_labels,
            font_size=8,
            font_color='darkred',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7)
        )
        
        # LÃ©gende
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', 
                      markerfacecolor=color, markersize=12, label=node_type.capitalize())
            for node_type, color in self.node_colors.items()
        ]
        plt.legend(handles=legend_elements, loc='upper left', fontsize=11)
        
        plt.title(title, fontsize=18, fontweight='bold', pad=20)
        plt.axis('off')
        plt.tight_layout()
        
        if filename:
            plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"âœ“ Graphe sauvegardÃ© dans {filename}")
        else:
            plt.show()
    
    def visualize_interactive(self, title: str = "Interactive RDF Graph"):
        """
        CrÃ©e une visualisation interactive du graphe RDF avec Plotly
        
        Args:
            title: Titre du graphe
            
        Returns:
            plotly.graph_objects.Figure: Figure Plotly interactive
        """
        if len(self.graph.nodes()) == 0:
            print("Le graphe est vide.")
            return None
        
        # Layout hiÃ©rarchique
        pos = nx.spring_layout(self.graph, k=2, iterations=50, seed=42)
        
        # PrÃ©parer les donnÃ©es pour Plotly
        edge_x = []
        edge_y = []
        edge_labels_list = []
        
        for u, v, data in self.graph.edges(data=True):
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x.append(x0)
            edge_x.append(x1)
            edge_x.append(None)
            edge_y.append(y0)
            edge_y.append(y1)
            edge_y.append(None)
            
            prop = data.get('property', '')
            edge_labels_list.append(prop.split(':')[-1])
        
        # CrÃ©er la trace des arÃªtes
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            mode='lines',
            line=dict(width=2, color='#555'),
            hoverinfo='text',
            text=edge_labels_list,
            name='Relations'
        )
        
        # PrÃ©parer les donnÃ©es des nÅ“uds par type
        nodes_by_type = {
            'resource': {'x': [], 'y': [], 'text': [], 'hover': []},
            'class': {'x': [], 'y': [], 'text': [], 'hover': []},
            'literal': {'x': [], 'y': [], 'text': [], 'hover': []},
            'property': {'x': [], 'y': [], 'text': [], 'hover': []},
        }
        
        color_map = {
            'resource': '#FF6B6B',  # Rouge
            'class': '#4ECDC4',     # Cyan
            'literal': '#98D8C8',   # Vert clair
            'property': '#FFA07A',  # Orange
        }
        
        size_map = {
            'class': 25,
            'resource': 20,
            'literal': 15,
            'property': 15,
        }
        
        symbol_map = {
            'resource': 'circle',
            'class': 'circle',
            'literal': 'square',
            'property': 'circle',
        }
        
        for node in self.graph.nodes():
            x, y = pos[node]
            entity = self.entities.get(node, {})
            label = entity.get('label', node)
            node_type = entity.get('type', 'resource')
            
            # CrÃ©er le texte de hover
            hover_text = f"<b>{label}</b><br>Type: {node_type}<br>URI: {node}"
            text_label = label.split(':')[-1][:15]
            
            if node_type in nodes_by_type:
                nodes_by_type[node_type]['x'].append(x)
                nodes_by_type[node_type]['y'].append(y)
                nodes_by_type[node_type]['text'].append(text_label)
                nodes_by_type[node_type]['hover'].append(hover_text)
        
        # CrÃ©er la figure
        fig = go.Figure(data=[edge_trace])
        
        # Ajouter une trace pour chaque type de nÅ“ud
        for node_type in ['resource', 'class', 'literal', 'property']:
            node_data = nodes_by_type[node_type]
            if node_data['x']:  # Si des nÅ“uds de ce type existent
                fig.add_trace(go.Scatter(
                    x=node_data['x'],
                    y=node_data['y'],
                    mode='markers+text',
                    text=node_data['text'],
                    textposition="top center",
                    textfont=dict(size=10, color='black'),
                    hoverinfo='text',
                    hovertext=node_data['hover'],
                    marker=dict(
                        symbol=symbol_map[node_type],
                        size=size_map[node_type],
                        color=color_map[node_type],
                        line_width=2,
                        line_color='black'
                    ),
                    name=node_type.capitalize(),
                    showlegend=True
                ))
        
        # Configurer la figure
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor='center'),
            showlegend=True,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='#f8f9fa',
            width=1000,
            height=700,
            clickmode='event+select'
        )
        
        return fig
    
    def print_summary(self):
        """Affiche un rÃ©sumÃ© du graphe RDF"""
        print("\n" + "="*70)
        print("RÃ‰SUMÃ‰ DU GRAPHE RDF")
        print("="*70)
        print(f"Nombre d'entitÃ©s: {len(self.entities)}")
        print(f"Nombre de relations: {len(self.properties)}")
        print()
        
        # Compter par type
        type_counts = {}
        for entity_id, entity_data in self.entities.items():
            entity_type = entity_data['type']
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        
        print("EntitÃ©s par type:")
        for entity_type, count in type_counts.items():
            print(f"  {entity_type}: {count}")
        print()
        
        print("Triples RDF:")
        for subj, pred, obj in self.properties:
            subj_label = self.entities.get(subj, {}).get('label', subj)
            obj_label = self.entities.get(obj, {}).get('label', obj)
            print(f"  {subj_label} --[{pred}]--> {obj_label}")
        print("="*70)
    
    def export_to_turtle(self, filename: str):
        """
        Exporte le graphe en format Turtle (RDF)
        
        Args:
            filename: Nom du fichier de sortie (.ttl)
        """
        with open(filename, 'w', encoding='utf-8') as f:
            # Ã‰crire les prÃ©fixes
            for prefix, uri in namespaces.items():
                f.write(f"@prefix {prefix}: <{uri}> .\n")
            f.write("\n")
            
            # Ã‰crire les triples
            for subj, pred, obj in self.properties:
                f.write(f"{subj} {pred} {obj} .\n")
        
        print(f"âœ“ Graphe exportÃ© en Turtle dans {filename}")