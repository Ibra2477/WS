"""
RDF Graph Builder - Construit un graphe RDF à partir d'une requête SPARQL
"""
import re
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Set
from .const.prefixes import namespaces, uri_to_prefixed, prefixed_to_uri


class RDFGraphBuilder:
    """Construit et visualise un graphe RDF à partir d'une requête SPARQL"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.entities = {}  # Mappe entity_id -> {type, label, uri}
        self.properties = []  # Liste des propriétés (sujet, prédicat, objet)
        
        # Couleurs pour différents types de nœuds
        self.node_colors = {
            'resource': '#FF6B6B',  # Rouge pour les ressources/entités
            'class': '#4ECDC4',     # Cyan pour les classes
            'literal': '#98D8C8',   # Vert clair pour les littéraux
            'property': '#FFA07A',  # Orange pour les propriétés
        }
    
    def parse_sparql_query(self, sparql_query: str) -> Dict:
        """
        Analyse une requête SPARQL pour extraire les entités, classes et patrons de triples.
        La sortie est structurée pour être réutilisable lors de la construction du graphe
        à partir des bindings réels (généralisation).
        """
        result = {
            'main_entity': None,
            'classes': [],          # [{variable: ?x, class: dbo:Song}]
            'triples': [],          # patrons de triples (sujet, prédicat, objet)
            'filters': []
        }

        where_match = re.search(r'WHERE\s*\{(.*?)\}', sparql_query, re.DOTALL | re.IGNORECASE)
        if not where_match:
            return result

        where_clause = where_match.group(1)

        # Capturer tous les triples (incluant rdf:type)
        triple_pattern = r'(\?\w+|<[^>]+>|[a-zA-Z_][\w-]*:[\w-]+)\s+(a|rdf:type|[a-zA-Z_][\w-]*:[\w-]+)\s+(\?\w+|<[^>]+>|"[^"]*"|[a-zA-Z_][\w-]*:[\w-]+)'
        for subj, pred, obj in re.findall(triple_pattern, where_clause, flags=re.IGNORECASE):
            subj = subj.strip()
            pred = pred.strip()
            obj = obj.strip()
            norm_pred = 'rdf:type' if pred in ['a', 'rdf:type'] else pred
            result['triples'].append({'subject': subj, 'predicate': norm_pred, 'object': obj})

            # Si rdf:type, mémoriser la classe principale pour la variable
            if norm_pred == 'rdf:type':
                result['classes'].append({'variable': subj, 'class': obj})

        # Identifier l'entité principale (première ressource nommée rencontrée)
        resource_pattern = r'(dbr:[A-Za-z_0-9]+)'
        resources = re.findall(resource_pattern, sparql_query)
        if resources:
            result['main_entity'] = resources[0]

        return result
    
    def build_from_sparql(self, sparql_query: str, natural_language: str = ""):
        """
        Construit le graphe RDF à partir d'une requête SPARQL
        
        Args:
            sparql_query: Requête SPARQL
            natural_language: Question en langage naturel (optionnel)
        """
        parsed = self.parse_sparql_query(sparql_query)
        
        # Ajouter les classes comme nœuds
        for class_info in parsed['classes']:
            var = class_info['variable']
            class_type = class_info['class']
            
            # Ajouter la classe comme nœud de type
            self.add_entity(class_type, 'class', class_type.split(':')[-1])
            
            # Ajouter la variable comme instance de cette classe
            self.add_entity(var, 'resource', var)
            self.add_property(var, 'rdf:type', class_type)
        
        # Ajouter l'entité principale
        if parsed['main_entity']:
            entity = parsed['main_entity']
            entity_name = entity.split(':')[-1].replace('_', ' ')
            self.add_entity(entity, 'resource', entity_name)
        
        # Ajouter les propriétés et relations
        for prop in parsed['properties']:
            subj = prop['subject']
            pred = prop['predicate']
            obj = prop['object']
            
            # Déterminer le type de l'objet
            if obj.startswith('?'):
                obj_type = 'resource'
            elif obj.startswith('"'):
                obj_type = 'literal'
                obj = obj.strip('"')
            else:
                obj_type = 'resource'
            
            # Ajouter les entités si elles n'existent pas
            if subj not in self.entities:
                self.add_entity(subj, 'resource', subj)
            if obj not in self.entities:
                self.add_entity(obj, obj_type, obj)
            
            # Ajouter la propriété
            self.add_property(subj, pred, obj)
    
    def build_from_results(self, sparql_query: str, results: dict, max_results: int = 20):
        """
        Construit le graphe RDF de manière générique à partir des résultats SPARQL.
        Exploite directement les patrons de triples de la requête pour relier les
        valeurs instanciées, quel que soit le domaine (capitales, chansons, personnes).
        """
        if not results or 'results' not in results or 'bindings' not in results['results']:
            print("Aucun résultat à traiter")
            return

        bindings = results['results']['bindings'][:max_results]
        parsed = self.parse_sparql_query(sparql_query)

        var_classes = {c['variable']: c['class'] for c in parsed.get('classes', [])}

        main_entity = parsed.get('main_entity')
        if main_entity:
            label = main_entity.split(':')[-1].replace('_', ' ')
            self.add_entity(main_entity, 'resource', label, prefixed_to_uri(main_entity))
        for _, cls in var_classes.items():
            class_label = cls.split(':')[-1]
            self.add_entity(cls, 'class', class_label, prefixed_to_uri(cls))

        def resolve_token(token: str, binding: Dict, idx: int) -> Optional[str]:
            """Résout un token (var, URI, prefixed, literal) en identifiant de nœud."""
            if token.startswith('?'):
                var = token[1:]
                if var not in binding:
                    return None
                val = binding[var]
                vtype, v = val.get('type'), val.get('value')
                if vtype == 'uri':
                    rid = uri_to_prefixed(v)
                    if rid == v:
                        rid = v.split('/')[-1]
                    label = rid.split(':')[-1].replace('_', ' ')
                    self.add_entity(rid, 'resource', label, v)
                    if token in var_classes:
                        self.add_property(rid, 'rdf:type', var_classes[token])
                    return rid
                if vtype == 'literal':
                    lid = f"literal_{idx}_{var}"
                    display = v[:80] + "..." if len(v) > 80 else v
                    self.add_entity(lid, 'literal', display)
                    return lid
                return None

            if token.startswith('<') and token.endswith('>'):
                uri = token.strip('<>')
                rid = uri_to_prefixed(uri)
                if rid == uri:
                    rid = uri.split('/')[-1]
                label = rid.split(':')[-1].replace('_', ' ')
                self.add_entity(rid, 'resource', label, uri)
                return rid

            label = token.split(':')[-1].replace('_', ' ')
            self.add_entity(token, 'resource', label, prefixed_to_uri(token))
            return token

        for idx, binding in enumerate(bindings):
            for triple in parsed.get('triples', []):
                subj_id = resolve_token(triple['subject'].strip(), binding, idx)
                obj_id = resolve_token(triple['object'].strip(), binding, idx)
                predicate = triple['predicate'].strip()

                if not subj_id or not obj_id:
                    continue

                if predicate == 'rdf:type' and obj_id.startswith('literal_'):
                    continue

                self.add_property(subj_id, predicate, obj_id)

        # Fallback : aucune arête créée
        if not self.properties and bindings:
            # On crée au moins des liens depuis l'entité principale (ou le premier URI) vers les autres
            binding = bindings[0]

            # Déterminer un noeud racine si main_entity absent
            root = main_entity
            if not root:
                for var_value in binding.values():
                    if var_value.get('type') == 'uri':
                        candidate = uri_to_prefixed(var_value['value'])
                        root = candidate
                        self.add_entity(candidate, 'resource', candidate.split(':')[-1].replace('_', ' '), var_value['value'])
                        break

            for var_name, var_value in binding.items():
                if var_value.get('type') == 'literal':
                    lid = f"literal_0_{var_name}"
                    display = var_value['value'][:80]
                    self.add_entity(lid, 'literal', display)
                    if root:
                        self.add_property(root, f'rdfs:{var_name}', lid)
                elif var_value.get('type') == 'uri':
                    rid = uri_to_prefixed(var_value['value'])
                    label = rid.split(':')[-1].replace('_', ' ')
                    self.add_entity(rid, 'resource', label, var_value['value'])
                    if root and rid != root:
                        self.add_property(root, f'linkedTo:{var_name}', rid)

            # Si toujours rien, relier tout au root
            if root:
                for entity_id in list(self.entities.keys()):
                    if entity_id == root:
                        continue
                    self.add_property(root, 'relatedTo', entity_id)

    def add_entity(self, entity_id: str, entity_type: str, label: str, uri: Optional[str] = None):
        """
        Ajoute une entité au graphe
        
        Args:
            entity_id: Identifiant unique de l'entité
            entity_type: Type de l'entité (resource, class, literal)
            label: Label lisible de l'entité
            uri: URI complète (optionnel)
        """
        self.graph.add_node(entity_id, type=entity_type, label=label)
        self.entities[entity_id] = {
            'type': entity_type,
            'label': label,
            'uri': uri or entity_id
        }
    
    def add_property(self, subject: str, predicate: str, obj: str):
        """
        Ajoute une propriété (triple RDF) au graphe
        
        Args:
            subject: Sujet du triple
            predicate: Prédicat (propriété)
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
        
        # Layout hiérarchique
        pos = nx.spring_layout(self.graph, k=3, iterations=50, seed=42)
        
        # Séparer les nœuds par type pour la coloration
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
        
        # Dessiner les nœuds
        nx.draw_networkx_nodes(
            self.graph, pos,
            node_color=node_colors,
            node_size=node_sizes,
            alpha=0.9,
            linewidths=2,
            edgecolors='black'
        )
        
        # Dessiner les arêtes
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
        
        # Labels des nœuds
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
        
        # Labels des arêtes (propriétés)
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
        
        # Légende
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
            print(f"✓ Graphe sauvegardé dans {filename}")
        else:
            plt.show()
    
    def print_summary(self):
        """Affiche un résumé du graphe RDF"""
        print("\n" + "="*70)
        print("RÉSUMÉ DU GRAPHE RDF")
        print("="*70)
        print(f"Nombre d'entités: {len(self.entities)}")
        print(f"Nombre de relations: {len(self.properties)}")
        print()
        
        # Compter par type
        type_counts = {}
        for entity_id, entity_data in self.entities.items():
            entity_type = entity_data['type']
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        
        print("Entités par type:")
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
        def fmt_resource(node_id: str) -> str:
            data = self.entities.get(node_id, {})
            uri = data.get('uri')
            if uri and uri.startswith('http'):
                return f"<{uri}>"
            return node_id

        def fmt_predicate(pred: str) -> str:
            # Si prédicat est une URI complète, l'encadrer, sinon laisser le préfixe
            if pred.startswith('http://') or pred.startswith('https://'):
                return f"<{pred}>"
            return pred

        def fmt_object(obj_id: str) -> str:
            if obj_id.startswith('literal_'):
                label = self.entities.get(obj_id, {}).get('label', obj_id)
                safe = label.replace('"', '\"')
                return f'"{safe}"'
            return fmt_resource(obj_id)

        with open(filename, 'w', encoding='utf-8') as f:
            for prefix, uri in namespaces.items():
                f.write(f"@prefix {prefix}: <{uri}> .\n")
            f.write("\n")

            for subj, pred, obj in self.properties:
                f.write(f"{fmt_resource(subj)} {fmt_predicate(pred)} {fmt_object(obj)} .\n")

        print(f"✓ Graphe exporté en Turtle dans {filename}")
