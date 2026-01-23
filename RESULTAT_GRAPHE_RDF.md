# Génération du Graphe RDF - Processus Détaillé

## 🎯 Flux Complet : Du Clic au Graphe

### **Étape 1 : Déclenchement (Interface Streamlit - app.py)**

Lorsque l'utilisateur clique sur le bouton **"📈 RDF Graph"** :

```python
if st.button("📈 RDF Graph", key=f"graph_new_{sparql_query[:50]}"):
```

**Actions immédiates :**

- Streamlit détecte le clic sur le bouton unique identifié par une clé basée sur la requête SPARQL
- Un spinner s'affiche : `"Generating RDF graph..."`
- Le processus entre dans un bloc `try/except` pour gérer les erreurs

---

### **Étape 2 : Initialisation du Constructeur RDF**

```python
rdf_builder = RDFGraphBuilder()
```

**Création de l'objet RDFGraphBuilder avec :**

- `self.graph = nx.DiGraph()` → Création d'un graphe orienté NetworkX vide
- `self.entities = {}` → Dictionnaire pour stocker les métadonnées des entités (type, label, URI)
- `self.properties = []` → Liste des triples RDF (sujet, prédicat, objet)
- `self.node_colors = {...}` → Palette de couleurs pour chaque type de nœud :
  - `'resource'` → Rouge (#FF6B6B)
  - `'class'` → Cyan (#4ECDC4)
  - `'literal'` → Vert clair (#98D8C8)
  - `'property'` → Orange (#FFA07A)

---

### **Étape 3 : Construction du Graphe depuis les Résultats**

```python
rdf_builder.build_from_results(sparql_query, raw_results, max_results=10)
```

#### **3.1 Validation des Données**

```python
if not results or 'results' not in results or 'bindings' not in results['results']:
    print("Aucun résultat à traiter")
    return
```

- Vérifie que `raw_results` contient la structure JSON attendue de DBpedia
- Extrait les 10 premiers résultats : `bindings = results['results']['bindings'][:10]`

#### **3.2 Parsing de la Requête SPARQL**

```python
parsed = self.parse_sparql_query(sparql_query)
```

Le parseur analyse la requête SPARQL pour extraire :

- **Entité principale** : Extraction via regex `<http://dbpedia.org/resource/...>`
  - Exemple : `Drake_(musician)` → `dbr:Drake (musician)`
- **Classe principale** : Détection des patterns `?x rdf:type dbo:Song` ou `?x a dbo:Song`
  - Exemple : `dbo:Song`
- **Propriétés** : Relations entre variables (ex: `dbo:artist`, `rdfs:label`)

#### **3.3 Ajout de l'Entité Principale**

```python
if main_entity:
    entity_name = main_entity.split(':')[-1].replace('_', ' ').replace('(musician)', '').strip()
    self.add_entity(main_entity, 'resource', entity_name, main_entity)
```

- Nettoie le nom : `Drake_(musician)` → `Drake`
- Ajoute le nœud dans le graphe avec le type `'resource'`
- Stocke dans `self.entities` avec l'URI complète

#### **3.4 Ajout de la Classe Principale**

```python
if main_class:
    class_name = main_class.split(':')[-1]
    self.add_entity(main_class, 'class', class_name)
```

- Extrait le nom : `dbo:Song` → `Song`
- Ajoute un nœud de type `'class'` (sera coloré en cyan)

#### **3.5 Traitement de Chaque Résultat (Boucle sur 10 éléments)**

Pour chaque binding dans les résultats :

**A. Détection du type de variable**

```python
for var_name, var_value in binding.items():
    value_type = var_value.get('type')  # 'uri' ou 'literal'
    value = var_value.get('value')
```

**B. Si c'est une URI (ressource DBpedia)**

```python
if value_type == 'uri':
    resource_id = uri_to_prefixed(value)
    # Conversion: http://dbpedia.org/resource/Evil_Ways → dbr:Evil_Ways

    label = resource_id.split(':')[-1].replace('_', ' ')
    # Extraction du nom lisible: Evil_Ways → Evil Ways

    self.add_entity(resource_id, 'resource', label, value)
    # Ajout du nœud dans le graphe
```

**C. Création des Relations (Triples RDF)**

```python
# Lien vers la classe
if main_class:
    self.add_property(resource_id, 'rdf:type', main_class)
    # Triple: dbr:Evil_Ways --[rdf:type]--> dbo:Song

# Lien vers l'entité principale
if main_entity:
    if 'artist' in sparql_query.lower():
        self.add_property(resource_id, 'dbo:artist', main_entity)
        # Triple: dbr:Evil_Ways --[dbo:artist]--> dbr:Drake
```

**D. Si c'est un Littéral (texte brut)**

```python
elif value_type == 'literal':
    literal_id = f"literal_{idx}_{var_name}"
    display_value = value[:50] + "..." if len(value) > 50 else value

    self.add_entity(literal_id, 'literal', display_value)

    # Lien entre la ressource et son label
    self.add_property(song_id, f'rdfs:{var_name}', literal_id)
    # Triple: dbr:Evil_Ways --[rdfs:label]--> "Evil Ways (Drake song)"
```

**Résultat de cette étape :**

- 1 nœud de classe (`dbo:Song`)
- 1 nœud pour l'artiste (`dbr:Drake`)
- 10 nœuds de ressources (chansons)
- 10 nœuds littéraux (titres)
- 30 arêtes (3 relations par chanson : type, artist, label)

---

### **Étape 4 : Génération du Nom de Fichier Unique**

```python
import time
filename = f"rdf_graph_{int(time.time())}"
```

- Utilise le timestamp Unix actuel (ex: `rdf_graph_1737649237`)
- Évite les conflits de noms de fichiers

---

### **Étape 5 : Export en Format Turtle (.ttl)**

```python
rdf_builder.export_to_turtle(filename + ".ttl")
```

#### **Processus d'Export :**

1. **Écriture des Préfixes**

```python
for prefix, uri in namespaces.items():
    f.write(f"@prefix {prefix}: <{uri}> .\n")
```

Génère :

```turtle
@prefix dbo: <http://dbpedia.org/ontology/> .
@prefix dbr: <http://dbpedia.org/resource/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
```

2. **Écriture des Triples RDF**

```python
for subj, pred, obj in self.properties:
    f.write(f"{subj} {pred} {obj} .\n")
```

Génère :

```turtle
dbr:Evil_Ways rdf:type dbo:Song .
dbr:Evil_Ways dbo:artist dbr:Drake .
dbr:Evil_Ways rdfs:label "Evil Ways (Drake song)" .
```

---

### **Étape 6 : Visualisation du Graphe (.png)**

```python
rdf_builder.visualize(filename + ".png", title="RDF Graph")
```

#### **6.1 Vérification**

```python
if len(self.graph.nodes()) == 0:
    print("Le graphe est vide.")
    return
```

#### **6.2 Création de la Figure**

```python
plt.figure(figsize=(16, 12))
```

- Canvas de 16x12 pouces pour une visualisation claire

#### **6.3 Calcul de la Disposition (Layout)**

```python
pos = nx.spring_layout(self.graph, k=3, iterations=50, seed=42)
```

- **Algorithme Spring Layout (Force-Directed)** :
  - Les nœuds se repoussent mutuellement
  - Les arêtes agissent comme des ressorts qui attirent les nœuds connectés
  - `k=3` : Distance optimale entre nœuds
  - `iterations=50` : Nombre d'itérations pour stabiliser
  - `seed=42` : Graine aléatoire pour reproductibilité
- Retourne un dictionnaire : `{node_id: (x, y)}`

#### **6.4 Préparation des Couleurs et Tailles**

```python
node_colors = []
node_sizes = []
for node in self.graph.nodes():
    node_type = self.entities.get(node, {}).get('type', 'resource')
    node_colors.append(self.node_colors.get(node_type, '#CCCCCC'))

    if node_type == 'class':
        node_sizes.append(3000)  # Classes plus grandes
    elif node_type == 'resource':
        node_sizes.append(2500)  # Ressources moyennes
    else:
        node_sizes.append(1500)  # Littéraux plus petits
```

#### **6.5 Dessin des Nœuds**

```python
nx.draw_networkx_nodes(
    self.graph, pos,
    node_color=node_colors,
    node_size=node_sizes,
    alpha=0.9,
    linewidths=2,
    edgecolors='black'
)
```

- Chaque nœud est dessiné avec sa couleur et taille spécifiques
- Contour noir de 2px pour la clarté

#### **6.6 Dessin des Arêtes (avec Flèches)**

```python
nx.draw_networkx_edges(
    self.graph, pos,
    edge_color='#333333',
    arrows=True,
    arrowsize=30,          # Taille des pointes de flèches
    arrowstyle='-|>',      # Style: ligne avec pointe triangulaire
    width=2.5,             # Épaisseur des lignes
    alpha=0.7,             # Transparence
    connectionstyle='arc3,rad=0.1',  # Courbure légère
    min_source_margin=25,  # Marge depuis le nœud source
    min_target_margin=25   # Marge avant le nœud cible
)
```

- **Flèches directionnelles** pour montrer le sens sujet → objet
- Courbure légère (`rad=0.1`) pour distinguer les arêtes parallèles

#### **6.7 Ajout des Labels de Nœuds**

```python
labels = {}
for node in self.graph.nodes():
    entity = self.entities.get(node, {})
    label = entity.get('label', node)
    # Simplifier les labels trop longs
    labels[node] = label.split(':')[-1].replace('_', ' ')[:20]

nx.draw_networkx_labels(
    self.graph, pos,
    labels,
    font_size=10,
    font_weight='bold',
    font_color='black'
)
```

- Affiche le nom lisible de chaque entité
- Tronque à 20 caractères pour éviter le chevauchement

#### **6.8 Ajout des Labels d'Arêtes (Propriétés)**

```python
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
```

- Affiche le nom de la propriété (ex: `artist`, `type`, `label`)
- Fond blanc arrondi pour la lisibilité

#### **6.9 Ajout de la Légende**

```python
legend_elements = [
    plt.Line2D([0], [0], marker='o', color='w',
              markerfacecolor=color, markersize=12, label=node_type.capitalize())
    for node_type, color in self.node_colors.items()
]
plt.legend(handles=legend_elements, loc='upper left', fontsize=11)
```

- Explique le code couleur : Resource, Class, Literal, Property

#### **6.10 Finalisation et Sauvegarde**

```python
plt.title(title, fontsize=18, fontweight='bold', pad=20)
plt.axis('off')
plt.tight_layout()
plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
```

- **DPI 300** : Haute résolution pour impression
- `bbox_inches='tight'` : Supprime les marges inutiles
- `facecolor='white'` : Fond blanc

---

### **Étape 7 : Affichage dans Streamlit**

```python
if os.path.exists(filename + ".png"):
    st.success("✅ RDF Graph generated successfully!")
    img = Image.open(filename + ".png")
    st.image(img, caption="RDF Graph Visualization", use_container_width=True)
```

1. **Vérification** que le fichier PNG existe
2. **Message de succès** affiché en vert
3. **Chargement de l'image** avec PIL (Pillow)
4. **Affichage** avec adaptation automatique à la largeur du conteneur

---

### **Étape 8 : Téléchargement du Fichier Turtle**

```python
with open(filename + ".ttl", "r") as f:
    turtle_content = f.read()
st.download_button(
    label="⬇️ Download Turtle RDF",
    data=turtle_content,
    file_name=filename + ".ttl",
    mime="text/turtle"
)
```

- Lecture du fichier Turtle généré
- Création d'un bouton de téléchargement Streamlit
- Type MIME `text/turtle` pour compatibilité avec les outils RDF

---

## 📊 Structures de Données Clés

### **1. self.entities (Dictionnaire)**

```python
{
    'dbr:Drake': {
        'type': 'resource',
        'label': 'Drake',
        'uri': 'http://dbpedia.org/resource/Drake_(musician)'
    },
    'dbo:Song': {
        'type': 'class',
        'label': 'Song'
    },
    'literal_0_title': {
        'type': 'literal',
        'label': 'Evil Ways (Drake song)'
    }
}
```

### **2. self.properties (Liste de Tuples)**

```python
[
    ('dbr:Evil_Ways', 'rdf:type', 'dbo:Song'),
    ('dbr:Evil_Ways', 'dbo:artist', 'dbr:Drake'),
    ('dbr:Evil_Ways', 'rdfs:label', 'literal_0_title')
]
```

### **3. self.graph (NetworkX DiGraph)**

```python
DiGraph avec:
- nodes: ['dbr:Drake', 'dbo:Song', 'dbr:Evil_Ways', 'literal_0_title', ...]
- edges: [
    ('dbr:Evil_Ways', 'dbo:Song', {'property': 'rdf:type'}),
    ('dbr:Evil_Ways', 'dbr:Drake', {'property': 'dbo:artist'})
  ]
```

---

## ⏱️ Complexité et Performance

| Étape               | Complexité         | Temps (10 résultats) |
| ------------------- | ------------------ | -------------------- |
| Parsing SPARQL      | O(n)               | ~5 ms                |
| Construction graphe | O(n × m)           | ~20 ms               |
| Layout Spring       | O(n² × iterations) | ~100-200 ms          |
| Rendu Matplotlib    | O(n + e)           | ~300-500 ms          |
| Export Turtle       | O(n + e)           | ~10 ms               |
| **TOTAL**           |                    | **~500-700 ms**      |

_n = nombre de nœuds, e = nombre d'arêtes, m = nombre de propriétés par résultat_

---

## 🎨 Encodage Visuel

| Élément      | Couleur        | Taille | Signification                         |
| ------------ | -------------- | ------ | ------------------------------------- |
| **Resource** | Rouge #FF6B6B  | 2500   | Entités DBpedia (Drake, chansons)     |
| **Class**    | Cyan #4ECDC4   | 3000   | Ontologies (Song, Album)              |
| **Literal**  | Vert #98D8C8   | 1500   | Valeurs textuelles (titres)           |
| **Property** | Orange #FFA07A | 2000   | Propriétés non utilisées actuellement |

