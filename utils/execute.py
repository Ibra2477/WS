from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd

sparql_apis = {
    "dbpedia": "https://dbpedia.org/sparql",
    "wikidata": "https://query.wikidata.org/sparql",
    "hal": "https://hal.archives-ouvertes.fr/sparql",
}

def execute_query(query: str, api="dbpedia") -> pd.DataFrame:
    assert api in sparql_apis, f"API {api} URL is not found."
    sparql = SPARQLWrapper(sparql_apis[api])
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return results

