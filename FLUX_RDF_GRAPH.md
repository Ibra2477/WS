# Flux du Clic sur "📈 RDF Graph"

## 🎯 Résumé Simple

Quand tu cliques sur le bouton **"📈 RDF Graph"** dans Streamlit :

```
Clic sur bouton
    ↓
Extraction des données (requête SPARQL + résultats)
    ↓
Construction du graphe RDF
    ↓
Génération 2 fichiers (PNG + TTL)
    ↓
Affichage du graphe PNG
    ↓
Bouton téléchargement du fichier TTL
```

---

## 📋 Étapes Détaillées

### **1️⃣ Détection du Clic**

```python
if st.button("📈 RDF Graph", key=f"graph_new_{sparql_query[:50]}"):
```

- Streamlit détecte le clic sur le bouton
- Affiche un spinner : `"Generating RDF graph..."`

### **2️⃣ Extraction des Données Existantes**

```python
rdf_builder = RDFGraphBuilder()
rdf_builder.build_from_results(sparql_query, raw_results, max_results=10)
```

**Entrées :**
- `sparql_query` : La requête SPARQL générée (ex: `SELECT ?capital WHERE { dbr:France dbo:capital ?capital }`)
- `raw_results` : Les résultats bruts de DBpedia (ex: `{"results": {"bindings": [{"capital": {"value": "http://dbpedia.org/resource/Paris"}}]}}`)

**Process :**
1. Parse la requête SPARQL pour extraire les **patrons de triples** (sujet, prédicat, objet)
2. Pour chaque binding (résultat), résout les variables en nœuds réels
3. Crée les arêtes (relations) entre nœuds
4. Stocke tout dans une structure NetworkX DiGraph

### **3️⃣ Génération du Nom de Fichier Unique**

```python
filename = f"rdf_graph_{int(time.time())}"
```

- Utilise le timestamp Unix pour éviter les conflits
- Exemple : `rdf_graph_1769161166`

### **4️⃣ Export en Deux Formats**

#### **A. Turtle RDF (.ttl)**
```python
rdf_builder.export_to_turtle(filename + ".ttl")
```

Génère un fichier texte formaté RDF :
```turtle
@prefix dbo: <http://dbpedia.org/ontology/> .
@prefix dbr: <http://dbpedia.org/resource/> .

<http://dbpedia.org/resource/France> dbo:capital <http://dbpedia.org/resource/Paris> .
```

#### **B. Image PNG (.png)**
```python
rdf_builder.visualize(filename + ".png", title="RDF Graph")
```

Génère une image NetworkX avec :
- 🔴 Nœuds colorés (ressources, classes, littéraux)
- ➜ Flèches directionnelles
- 🏷️ Labels des relations (ex: `capital`)

### **5️⃣ Vérification du Fichier PNG**

```python
if os.path.exists(filename + ".png"):
```

- S'assure que le fichier PNG a bien été créé

### **6️⃣ Affichage du Graphe dans Streamlit**

```python
st.success("✅ RDF Graph generated successfully!")
img = Image.open(filename + ".png")
st.image(img, caption="RDF Graph Visualization", use_container_width=True)
```

- Affiche un message de succès en vert
- Charge l'image PNG
- L'affiche dans Streamlit avec adaptation à la largeur

### **7️⃣ Bouton de Téléchargement**

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

- Lit le fichier TTL généré
- Crée un bouton Streamlit pour télécharger
- Type MIME : `text/turtle` pour compatibilité

---

## 📊 Exemple Complet : "What is the capital of France?"

### **Input**
```
Requête SPARQL :
  SELECT ?capital WHERE { dbr:France dbo:capital ?capital }

Résultats DBpedia :
  [{"capital": {"value": "http://dbpedia.org/resource/Paris"}}]
```

### **Processing**
1. **Parse SPARQL** → 1 triple trouvé : `dbr:France dbo:capital ?capital`
2. **Résout bindings** :
   - `dbr:France` → nœud "France" (type: resource)
   - `?capital` → résout en `http://dbpedia.org/resource/Paris` → nœud "Paris"
   - prédicat : `dbo:capital`
3. **Crée arête** : France --[dbo:capital]--> Paris

### **Output Files**
```
rdf_graph_1769161166.ttl :
  <http://dbpedia.org/resource/France> dbo:capital <http://dbpedia.org/resource/Paris> .

rdf_graph_1769161166.png :
  [Image montrant deux nœuds avec une flèche "capital" entre eux]
```

### **Affichage Streamlit**
1. ✅ Message de succès
2. 📊 Image PNG du graphe
3. ⬇️ Bouton de téléchargement TTL

---

## 🔧 Gestion des Erreurs

```python
except Exception as e:
    st.error(f"❌ Error generating RDF graph: {str(e)}")
```

Si quelque chose échoue (erreur de parsing, fichier non créé, etc.), un message d'erreur rouge s'affiche.

---

## 📈 Fichiers Générés

| Fichier | Format | Contenu | Usage |
|---------|--------|---------|-------|
| `rdf_graph_*.ttl` | Texte | Triples RDF en format Turtle | Import dans outils RDF, analyse sémantique |
| `rdf_graph_*.png` | Image | Visualisation du graphe | Présentation, documentation |

---

## ⏱️ Temps Total

- **Parsing SPARQL** : ~5ms
- **Construction graphe** : ~20ms
- **Rendu PNG** : ~300-500ms
- **Sauvegarde fichiers** : ~10ms
- **Total** : ~400-600ms (affichage du spinner pendant ce temps)

