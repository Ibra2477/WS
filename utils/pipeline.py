from utils.clustering_llm import analyse_universelle
from utils.execute import execute_query


def pipeline_complet(query, api="dbpedia", n_clusters=3):
    # Étape 1 : Récupération des données via l'API choisie
    print(f"Exécution de la requête sur {api}...")
    resultats_json = execute_query(query, api)
    
    # Étape 2 : Analyse et Clustering
    print("Analyse sémantique et génération du graphique...")
    df_analysed, fig = analyse_universelle(resultats_json)
    
    # Étape 3 : Affichage
    if fig:
        fig.show()
    
    return df_analysed

# --- EXEMPLE D'UTILISATION RÉELLE ---
ma_requete = """
SELECT DISTINCT ?name ?universityName ?birthDate
WHERE {
  ?artist a dbo:MusicalArtist .
  ?artist rdfs:label ?name .
  ?artist dbo:almaMater ?university .
  ?university rdfs:label ?universityName .
  ?artist dbo:birthDate ?birthDate .
  FILTER (lang(?name) = "en" AND lang(?universityName) = "en")
  FILTER (?birthDate > "1970-01-01"^^xsd:date)
}
LIMIT 50
"""

# Une seule ligne pour tout faire !
df_final = pipeline_complet(ma_requete, api="dbpedia")