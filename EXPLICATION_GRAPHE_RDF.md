# 📊 Explication Détaillée : Construction et Visualisation du Graphe RDF

## 🎯 Vue d'Ensemble

Un **graphe RDF** est une représentation visuelle et structurée des données sémantiques. Au lieu d'avoir des résultats plats (une liste), on a **des relations entre entités**.

**Exemple :**
```
Au lieu de : "Paris" (juste un texte)
On a       : France --[capital]--> Paris (une relation claire)
```

---

## 🏗️ Architecture du Graphe RDF

### **Composants Principaux**

```
┌─────────────────────────────────────┐
│         GRAPHE RDF                  │
├─────────────────────────────────────┤
│                                     │
│  NŒUDS (Nodes)                     │
│  ├─ France (ressource)             │
│  ├─ Paris (ressource)              │
│  ├─ Capital (classe)               │
│  └─ "Paris" (littéral/texte)       │
│                                     │
│  ARÊTES (Edges)                    │
│  ├─ France --[capital]--> Paris    │
│  ├─ Paris --[type]--> Capital      │
│  └─ Paris --[label]--> "Paris"     │
│                                     │
└─────────────────────────────────────┘
```

### **Structure d'un Triple RDF**

Chaque arête représente un **triple RDF** (sujet, prédicat, objet) :

```
┌──────────────────────────────────────┐
│  Sujet      Prédicat        Objet    │
├──────────────────────────────────────┤
│  France  →  dbo:capital  →  Paris    │
│                                      │
│  Nœud1       Relation       Nœud2    │
└──────────────────────────────────────┘
```

---

## 🔧 Processus de Construction (Détaillé)

### **Étape 1 : Parse de la Requête SPARQL**

**Entrée :** La requête SPARQL générée

```sparql
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbr: <http://dbpedia.org/resource/>

SELECT ?capital WHERE {
    dbr:France dbo:capital ?capital .
}
```

**Code :**
```python
def parse_sparql_query(self, sparql_query: str) -> Dict:
    where_match = re.search(r'WHERE\s*\{(.*?)\}', sparql_query, re.DOTALL)
    where_clause = where_match.group(1)
    
    # Chercher les triples avec regex
    triple_pattern = r'(\?\w+|<[^>]+>|[a-zA-Z_][\w-]*:[\w-]+)\s+(a|rdf:type|[a-zA-Z_][\w-]*:[\w-]+)\s+(\?\w+|<[^>]+>|"[^"]*"|[a-zA-Z_][\w-]*:[\w-]+)'
    
    for subj, pred, obj in re.findall(triple_pattern, where_clause):
        result['triples'].append({
            'subject': subj,      # dbr:France
            'predicate': pred,    # dbo:capital
            'object': obj         # ?capital
        })
```

**Résultat :**
```python
triples = [
    {
        'subject': 'dbr:France',
        'predicate': 'dbo:capital',
        'object': '?capital'
    }
]
```

### **Étape 2 : Extraction des Résultats**

**Entrée :** Résultats bruts de DBpedia

```json
{
  "results": {
    "bindings": [
      {
        "capital": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/Paris"
        }
      }
    ]
  }
}
```

**Extraction :**
```python
bindings = results['results']['bindings'][:max_results]
# Limite à 10 résultats pour la lisibilité

# bindings[0] = {'capital': {'type': 'uri', 'value': 'http://dbpedia.org/resource/Paris'}}
```

### **Étape 3 : Résolution des Tokens**

**Concept clé :** Transformer les patrons de la SPARQL en entités réelles

```python
def resolve_token(token: str, binding: Dict) -> str:
    """
    Transforme un token SPARQL en nœud du graphe
    
    Exemples :
    - '?capital' + binding → 'dbr:Paris' (ressource)
    - 'dbr:France' → 'dbr:France' (ressource nommée)
    - '"Paris"' → 'literal_0_capital' (littéral)
    """
```

**Cas 1 : Variable (?capital)**
```python
if token.startswith('?'):
    var = token[1:]  # "capital"
    if var in binding:
        val = binding[var]  # {'type': 'uri', 'value': '...'}
        vtype = val.get('type')  # 'uri'
        v = val.get('value')      # 'http://dbpedia.org/resource/Paris'
        
        if vtype == 'uri':
            # Convertir en format préfixé
            rid = uri_to_prefixed(v)  # 'dbr:Paris'
            label = rid.split(':')[-1].replace('_', ' ')  # 'Paris'
            
            # Ajouter le nœud au graphe
            self.add_entity(rid, 'resource', label, v)
            return rid  # 'dbr:Paris'
```

**Cas 2 : Ressource Nommée (dbr:France)**
```python
if not token.startswith('?'):
    # C'est déjà une ressource (pas une variable)
    label = token.split(':')[-1].replace('_', ' ')  # 'France'
    self.add_entity(token, 'resource', label, prefixed_to_uri(token))
    return token  # 'dbr:France'
```

**Cas 3 : URI Complète (<http://...>)**
```python
if token.startswith('<') and token.endswith('>'):
    uri = token.strip('<>')
    rid = uri_to_prefixed(uri)  # Convertir en format préfixé
    # ... même processus
    return rid
```

### **Étape 4 : Construction des Arêtes**

Pour chaque **triple patron** + **binding** :

```python
for idx, binding in enumerate(bindings):
    for triple in parsed['triples']:
        
        # Résoudre sujet et objet
        subject = resolve_token(triple['subject'], binding, idx)
        # Result: 'dbr:France'
        
        obj = resolve_token(triple['object'], binding, idx)
        # Result: 'dbr:Paris'
        
        predicate = triple['predicate']
        # Result: 'dbo:capital'
        
        # Créer l'arête
        if subject and obj:
            self.add_property(subject, predicate, obj)
            # Ajoute : France --[dbo:capital]--> Paris
```

### **Étape 5 : Stockage des Entités et Relations**

**Structure de données :**

```python
self.entities = {
    'dbr:France': {
        'type': 'resource',
        'label': 'France',
        'uri': 'http://dbpedia.org/resource/France'
    },
    'dbr:Paris': {
        'type': 'resource',
        'label': 'Paris',
        'uri': 'http://dbpedia.org/resource/Paris'
    }
}

self.properties = [
    ('dbr:France', 'dbo:capital', 'dbr:Paris')
]

self.graph = NetworkX.DiGraph(
    nodes=['dbr:France', 'dbr:Paris'],
    edges=[('dbr:France', 'dbr:Paris', {'property': 'dbo:capital'})]
)
```

---

## 🎨 Visualisation du Graphe

### **Processus de Rendu**

```python
def visualize(self, filename: str, title: str):
    # 1. Créer une figure
    plt.figure(figsize=(16, 12))
    
    # 2. Calculer le layout (position des nœuds)
    pos = nx.spring_layout(self.graph, k=3, iterations=50, seed=42)
    
    # 3. Dessiner les éléments
    # 4. Ajouter les labels
    # 5. Sauvegarder
```

### **Étape A : Calcul du Layout (Spring Layout)**

**Algorithme Force-Directed :**

Les nœuds se repoussent mutuellement, les arêtes les attirent comme des ressorts.

```
Itération 1:    Itération 10:    Itération 50:
  F    P         F - P           F ========= P
  |              |               
  |              |
```

**Paramètres :**
- `k=3` : Distance optimale entre nœuds (3 unités)
- `iterations=50` : Nombre d'itérations pour stabiliser
- `seed=42` : Graine aléatoire (reproductibilité)

**Résultat :** Dictionnaire `{node_id: (x, y)}`

### **Étape B : Coloration des Nœuds**

```python
node_colors = []
node_sizes = []

for node in self.graph.nodes():
    entity_type = self.entities[node]['type']
    
    if entity_type == 'class':
        color = '#4ECDC4'  # Cyan
        size = 3000        # Grand
    elif entity_type == 'resource':
        color = '#FF6B6B'  # Rouge
        size = 2500        # Moyen
    else:  # literal
        color = '#98D8C8'  # Vert
        size = 1500        # Petit
    
    node_colors.append(color)
    node_sizes.append(size)
```

**Code couleur :**
```
🔴 Resources (dbr:France, dbr:Paris) : Rouge #FF6B6B
🔵 Classes (dbo:Song, dbo:Capital) : Cyan #4ECDC4
🟢 Literals ("Paris", "France") : Vert #98D8C8
```

### **Étape C : Dessin des Nœuds**

```python
nx.draw_networkx_nodes(
    self.graph, pos,
    node_color=node_colors,
    node_size=node_sizes,
    alpha=0.9,              # Opacité 90%
    linewidths=2,           # Contour épais
    edgecolors='black'      # Contour noir
)
```

**Résultat :**
```
┌─────────┐
│ France  │  (cercle rouge, 2500px)
└─────────┘
```

### **Étape D : Dessin des Arêtes (avec Flèches)**

```python
nx.draw_networkx_edges(
    self.graph, pos,
    edge_color='#333333',      # Gris foncé
    arrows=True,               # Afficher flèches
    arrowsize=30,              # Taille pointe (30px)
    arrowstyle='-|>',          # Style : ligne + triangle
    width=2.5,                 # Épaisseur arête
    alpha=0.7,                 # Transparence 70%
    connectionstyle='arc3,rad=0.1',  # Courbure légère
    min_source_margin=25,      # Marge depuis source
    min_target_margin=25       # Marge avant cible
)
```

**Résultat :**
```
France ════════════════════➜ Paris
       (arête courbe avec flèche)
```

### **Étape E : Ajout des Labels de Nœuds**

```python
labels = {}
for node in self.graph.nodes():
    label = self.entities[node]['label']  # 'France', 'Paris'
    labels[node] = label[:20]  # Tronquer si trop long

nx.draw_networkx_labels(
    self.graph, pos,
    labels,
    font_size=10,
    font_weight='bold',
    font_color='black'
)
```

**Résultat :**
```
┌─────────┐
│ France  │  ← Le label "France" affiché
└─────────┘
```

### **Étape F : Ajout des Labels d'Arêtes (Relation)**

```python
edge_labels = {}
for u, v, data in self.graph.edges(data=True):
    prop = data.get('property', '')  # 'dbo:capital'
    edge_labels[(u, v)] = prop.split(':')[-1]  # 'capital'

nx.draw_networkx_edge_labels(
    self.graph, pos,
    edge_labels,
    font_size=8,
    font_color='darkred',
    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7)
)
```

**Résultat :**
```
France ════[capital]════➜ Paris
       (label rouge sur fond blanc)
```

### **Étape G : Légende et Finalisations**

```python
legend_elements = [
    plt.Line2D([0], [0], marker='o', color='w', 
              markerfacecolor='#FF6B6B', markersize=12, label='Resource'),
    plt.Line2D([0], [0], marker='o', color='w', 
              markerfacecolor='#4ECDC4', markersize=12, label='Class'),
    plt.Line2D([0], [0], marker='o', color='w', 
              markerfacecolor='#98D8C8', markersize=12, label='Literal')
]
plt.legend(handles=legend_elements, loc='upper left', fontsize=11)
plt.title(title, fontsize=18, fontweight='bold')
plt.axis('off')  # Pas d'axes
plt.tight_layout()
plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
```

---

## 📤 Export en Format Turtle (.ttl)

### **Format Standard RDF**

```turtle
@prefix dbo: <http://dbpedia.org/ontology/> .
@prefix dbr: <http://dbpedia.org/resource/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://dbpedia.org/resource/France> dbo:capital <http://dbpedia.org/resource/Paris> .
<http://dbpedia.org/resource/Paris> rdfs:label "Paris" .
```

### **Processus d'Export**

```python
def export_to_turtle(self, filename: str):
    with open(filename, 'w') as f:
        # 1. Écrire les préfixes
        for prefix, uri in namespaces.items():
            f.write(f"@prefix {prefix}: <{uri}> .\n")
        f.write("\n")
        
        # 2. Écrire les triples
        for subject, predicate, obj in self.properties:
            # Formater sujet (URI avec < >)
            if subject.startswith('http'):
                subj_str = f"<{subject}>"
            else:
                subj_str = subject
            
            # Formater objet
            if obj.startswith('literal_'):
                # C'est un littéral, le mettre entre guillemets
                label = self.entities[obj]['label']
                obj_str = f'"{label}"'
            else:
                # C'est une ressource, le mettre entre < >
                obj_str = f"<{self.entities[obj]['uri']}>"
            
            # Écrire le triple
            f.write(f"{subj_str} {predicate} {obj_str} .\n")
```

---

## 🔍 Exemple Complet : "What is the capital of France?"

### **Entrée Complète**

**SPARQL Query :**
```sparql
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbr: <http://dbpedia.org/resource/>
SELECT ?capital WHERE {
    dbr:France dbo:capital ?capital .
}
```

**DBpedia Results :**
```json
{
  "results": {
    "bindings": [
      {
        "capital": {
          "type": "uri",
          "value": "http://dbpedia.org/resource/Paris"
        }
      }
    ]
  }
}
```

### **Exécution Pas à Pas**

**1. Parse SPARQL :**
```
Triple trouvé : dbr:France --[dbo:capital]--> ?capital
```

**2. Extraction binding :**
```
binding[0] = {
  'capital': {
    'type': 'uri',
    'value': 'http://dbpedia.org/resource/Paris'
  }
}
```

**3. Résolution des tokens :**
```
Sujet    : dbr:France → resolve_token('dbr:France', binding) → 'dbr:France'
Objet    : ?capital → resolve_token('?capital', binding) → 'dbr:Paris'
Prédicat : dbo:capital
```

**4. Création nœuds :**
```python
self.add_entity('dbr:France', 'resource', 'France', 'http://...')
self.add_entity('dbr:Paris', 'resource', 'Paris', 'http://...')
```

**5. Création arête :**
```python
self.add_property('dbr:France', 'dbo:capital', 'dbr:Paris')
```

**6. Rendu PNG :**
```
Layout : France et Paris positionnés
Dessiner : France (rouge) ═══[capital]═══➜ Paris (rouge)
```

**7. Export TTL :**
```turtle
<http://dbpedia.org/resource/France> dbo:capital <http://dbpedia.org/resource/Paris> .
```

### **Résultat Final**

| Fichier | Contenu |
|---------|---------|
| **PNG** | Graphe visuel : France --capital--> Paris |
| **TTL** | `<...France> dbo:capital <...Paris> .` |

---

## 🧩 Types de Nœuds et Relations

### **Types de Nœuds**

| Type | Couleur | Exemple | Usage |
|------|---------|---------|-------|
| **Resource** | 🔴 Rouge | dbr:France, dbr:Paris | Entités réelles |
| **Class** | 🔵 Cyan | dbo:Song, dbo:Capital | Types/Ontologies |
| **Literal** | 🟢 Vert | "Paris", "2.2M" | Valeurs texte/nombre |

### **Types de Relations**

| Relation | Signification | Exemple |
|----------|---------------|---------|
| `dbo:capital` | A pour capitale | France --capital--> Paris |
| `rdf:type` | Est instance de | Paris --type--> City |
| `rdfs:label` | Nom textuel | Paris --label--> "Paris" |
| `dbo:artist` | Créateur | Song --artist--> Drake |

---

## 📊 Statistiques du Graphe

Après la construction, on peut afficher un résumé :

```
RÉSUMÉ DU GRAPHE RDF
═══════════════════════
Nombre d'entités: 2
Nombre de relations: 1

Entités par type:
  resource: 2

Triples RDF:
  France --[dbo:capital]--> Paris
═══════════════════════
```

---

## ⚡ Performance et Optimisations

| Étape | Temps | Optimisation |
|-------|-------|--------------|
| Parse SPARQL | ~5ms | Regex compilée |
| Résolution tokens | ~5ms | HashMap lookups |
| Construction graphe | ~10ms | Ajout incrémental |
| Layout (Spring) | ~200-300ms | Iterations=50, k=3 |
| Rendu PNG | ~200-300ms | DPI=300, tight_layout |
| Export TTL | ~10ms | Écriture séquentielle |
| **TOTAL** | **~500-700ms** | **Acceptable pour UI** |

---

## 🚀 Concepts Avancés

### **Généricité**

L'algorithme fonctionne pour **n'importe quel domaine** :
- Capitales : France --capital--> Paris
- Chansons : Drake --sings--> Song_A
- Films : Spielberg --directs--> Movie_B
- Personnes : Obama --birthPlace--> Hawaii

**Pourquoi ?** Pas d'heuristiques spécifiques au domaine, juste les patrons de triples.

### **Scalabilité**

Pour les graphes très grands :
- **Max 10 résultats** (limite paramétrable)
- **Layouts parallélisés** (pas implémenté, mais possible)
- **Export incrémental** (streaming pour très gros TTL)

---

## 🎓 Résumé Visuel

```
Question en Français
        ↓
    SPARQL Query
        ↓
    Résultats DBpedia (JSON)
        ↓
    ┌─────────────────────────────────┐
    │  RDF Graph Builder              │
    │  ├─ Parse SPARQL               │
    │  ├─ Résout les bindings        │
    │  ├─ Crée nœuds & arêtes        │
    │  └─ Structure GraphDB          │
    └─────────────────────────────────┘
        ↓
    ┌────────────────┬────────────────┐
    ↓                ↓
  PNG             TTL
(Visuel)      (Format RDF)
  ↓                ↓
Affiche        Export
Streamlit      Standard

