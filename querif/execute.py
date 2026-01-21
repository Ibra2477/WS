from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd

DBPEDIA_API = "https://dbpedia.org/sparql"


def execute_query(query: str) -> pd.DataFrame:
    sparql = SPARQLWrapper(DBPEDIA_API)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return results
