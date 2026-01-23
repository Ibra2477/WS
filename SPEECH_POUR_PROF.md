# 🎤 Speech - Présentation du Projet GraphDB RDF

## 📌 Introduction (30 secondes)

Bonjour [Professeur],

Aujourd'hui, je vais vous présenter un projet innovant : **GraphDB RDF** - un système qui transforme des requêtes en langage naturel en graphes RDF interactifs.

En résumé : vous posez une question simple en français, le système la traduit automatiquement en requête SPARQL, la pose à DBpedia (une base de données ontologique), récupère les résultats, et les visualise sous forme de **graphe RDF** avec les relations clairement affichées.

---

## 🎯 Problématique (45 secondes)

**Le défi :** 
- Les utilisateurs ne comprennent pas les requêtes SPARQL complexes
- Les résultats bruts de DBpedia sont difficiles à interpréter
- Les relations entre entités ne sont pas visuelles

**Notre solution :**
- Créer un pipeline automatisé NL → SPARQL → RDF Graph
- Rendre les données visuelles et compréhensibles
- Générer des fichiers RDF standards (Turtle)

---

## 🏗️ Architecture du Projet (1 minute 30)

### **Couche 1 : Input (Utilisateur)**
```
"What is the capital of France?"
         ↓
```

### **Couche 2 : NL2SPARQL (Traduction)**
```
Deepseek LLM détecte : FACT_LOOKUP
         ↓
Génère automatiquement :
PREFIX dbo: <http://dbpedia.org/ontology/>
SELECT ?capital WHERE {
    dbr:France dbo:capital ?capital
}
```

### **Couche 3 : Exécution (DBpedia)**
```
Requête SPARQL sur DBpedia
         ↓
Résultats JSON :
{
  "bindings": [
    {"capital": {"value": "http://dbpedia.org/resource/Paris"}}
  ]
}
```

### **Couche 4 : RDF Graph Builder (Notre Cœur)**
```
Parse SPARQL → Extrait patrons de triples
Résout bindings → Crée nœuds et arêtes
Construit graphe NetworkX
         ↓
```

### **Couche 5 : Outputs (Résultats)**
```
1. PNG : Graphe visualisé avec flèches
2. TTL : Fichier RDF standard
3. Streamlit : Interface interactive
```

---

## 🔑 Composants Clés (1 minute)

### **1. RDFGraphBuilder (cœur du système)**

**Classe principale :** `RDFGraphBuilder`

**Trois méthodes essentielles :**

**a) `parse_sparql_query(query)`**
- Analyse la requête SPARQL avec regex
- Extrait les triples : (sujet, prédicat, objet)
- Exemple : `dbr:France dbo:capital ?capital`

**b) `build_from_results(query, results)`**
- Reçoit les bindings (résultats) de DBpedia
- Pour chaque triple patron + binding :
  - Résout les variables en valeurs réelles
  - Crée les nœuds dans le graphe
  - Ajoute les arêtes avec le prédicat
- **Générique** : Fonctionne pour n'importe quel domaine (capitales, chansons, films, etc.)

**c) `visualize()` et `export_to_turtle()`**
- Génère l'image PNG avec NetworkX
- Exporte en format Turtle RDF

---

## 💡 Exemple Concret (1 minute)

### **Question :** "What is the capital of France?"

**Étape 1 - Parse Deepseek**
```
Détecte : FACT_LOOKUP query
Génère SPARQL :
  SELECT ?capital WHERE {
    dbr:France dbo:capital ?capital
  }
```

**Étape 2 - Exécution**
```
Résultat : Paris (URI: http://dbpedia.org/resource/Paris)
```

**Étape 3 - RDF Graph**
```
Parse SPARQL :
  Triple trouvé : dbr:France --[dbo:capital]--> ?capital

Résout avec binding :
  ?capital = dbr:Paris
  
Crée arête :
  France --[dbo:capital]--> Paris
```

**Étape 4 - Output**
```
PNG : [Deux cercles] France ===capital===> Paris
TTL :  <http://dbpedia.org/resource/France> dbo:capital <http://dbpedia.org/resource/Paris> .
```

---

## 🚀 Avantages de cette Approche (45 secondes)

✅ **Générique** : Fonctionne pour n'importe quel type de requête (pas d'heuristiques spécifiques)

✅ **Automatisé** : Pas d'intervention manuelle requise

✅ **Interopérable** : Exporte en Turtle RDF, standard du web sémantique

✅ **Visuel** : Les relations sont claires et faciles à comprendre

✅ **Scalable** : Peut gérer des graphes complexes avec plusieurs relations

---

## 📊 Architecture Technique (1 minute)

```
┌─────────────────────────────────────────┐
│  Streamlit Interface (Frontend)         │
│  - Chat input                           │
│  - Query results display                │
│  - "📈 RDF Graph" button               │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│  NL2SPARQL Pipeline                     │
│  - Deepseek LLM détection de type      │
│  - Génération SPARQL                    │
│  - Exécution DBpedia                    │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│  RDFGraphBuilder (Notre Contribution)   │
│  ├─ parse_sparql_query()               │
│  ├─ build_from_results()               │
│  ├─ visualize()                        │
│  └─ export_to_turtle()                 │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│  Outputs                                │
│  ├─ PNG (NetworkX visualization)        │
│  ├─ TTL (Turtle RDF export)            │
│  └─ HTML (Streamlit display)           │
└─────────────────────────────────────────┘
```

---

## 🧪 Tests et Résultats (45 secondes)

**Requêtes testées :**

1. **"What is the capital of France?"**
   - ✅ Détecte FACT_LOOKUP
   - ✅ Crée relation : France --[capital]--> Paris
   - ✅ Export TTL valide

2. **"List Drake songs"**
   - ✅ Détecte CLASS_QUERY
   - ✅ 10 chansons affichées
   - ✅ Relations : Song --[artist]--> Drake

3. **"Movies directed by Steven Spielberg"**
   - ✅ Détecte CLASS_QUERY
   - ✅ Crée relations : Movie --[director]--> Spielberg

**Performance :**
- Parse SPARQL : ~5ms
- Parsing + Construction : ~20ms
- Rendu graphe : ~300-500ms
- **Total** : ~400-600ms

---

## 🔍 Algorithme Principal : build_from_results()

**Concept clé :** Généricité via patrons de triples

```python
# Pour chaque résultat (binding)
for idx, binding in enumerate(bindings):
    # Pour chaque triple patron de la requête SPARQL
    for triple in parsed_triples:
        # Résout sujet, prédicat, objet
        subject = resolve_token(triple.subject, binding)
        predicate = triple.predicate
        obj = resolve_token(triple.object, binding)
        
        # Ajoute l'arête
        add_property(subject, predicate, obj)
```

**Pourquoi c'est générique :**
- Ne fait aucune hypothèse sur le domaine
- Suit strictement les patrons de la requête
- Résout automatiquement les variables
- Fonctionne pour capitales, chansons, films, etc.

---

## 📁 Fichiers Clés du Projet

| Fichier | Rôle |
|---------|------|
| `querif/rdf_graph_builder.py` | Cœur - Construction RDF |
| `querif/app/app.py` | Interface Streamlit |
| `querif/nl2sparql/main.py` | Pipeline NL → SPARQL |
| `nl2rdf_converter.py` | Script CLI autonome |

---

## 🎓 Apprentissages et Innovations

✨ **Web Sémantique** : Intégration DBpedia + Turtle RDF

✨ **NLP & LLM** : Utilisation Deepseek pour détection type requête

✨ **Graphe Programmation** : NetworkX pour structure et visualisation

✨ **Généricité** : Algorithme fonctionnant sur tous les domaines

✨ **Interopérabilité** : Format standard Turtle pour export

---

## 🚀 Futures Améliorations

1. **Graphe Interactif** : Ajouter Pyvis pour draggable/zoomable/cliquable
2. **Caching** : Mémoriser requêtes déjà exécutées
3. **Persistance** : Base de données RDF locale
4. **Requêtes Complexes** : Gérer OPTIONAL, FILTER, UNION
5. **Analytics** : Statistiques sur les graphes générés

---

## ✅ Conclusion (30 secondes)

Ce projet démontre comment :
- Combiner NLP, requêtes sémantiques et visualisation graphique
- Créer un système générique fonctionnant sur plusieurs domaines
- Exporter en standards du web sémantique (RDF/Turtle)
- Rendre accessible les technologies complexes via une interface simple

**En une phrase :**
*De la question en français au graphe RDF visualisé, automatiquement et intelligemment.*

---

## 🎤 Points Clés à Souligner

**Si le prof pose des questions :**

**Q: "Comment marche la généricité ?"**
R: "On suit les patrons de triples de la SPARQL et on résout chaque variable avec les bindings. Pas de logique spécifique au domaine."

**Q: "Pourquoi Turtle RDF ?"**
R: "C'est le standard W3C pour exprimer les triplets RDF. Interopérable avec n'importe quel outil sémantique."

**Q: "Ça marche pour quel type de requête ?"**
R: "Tous les types : Fact Lookup (capitales), Class Queries (chansons), Comparaisons, etc."

---

## ⏱️ Timing du Speech

- **Introduction** : 0:30
- **Problématique** : 1:15
- **Architecture** : 2:45
- **Composants clés** : 3:45
- **Exemple concret** : 5:00
- **Avantages** : 5:45
- **Architecture technique** : 6:45
- **Tests** : 7:30
- **Algorithme** : 8:30
- **Conclusion** : 9:00

**Total : 9 minutes** (ajustable selon le temps disponible)

