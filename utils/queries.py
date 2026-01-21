prefixes = {
    "dbpedia": """
PREFIX dbr:  <http://dbpedia.org/resource/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dbo:  <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>
""",
    "hal": """
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX hal: <http://data.archives-ouvertes.fr/schema/>,
""",
    "wikidata": """
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
""",
}

# dict for predefined SPARQL requests
# each key is a label, each value is a dict with "req" and "desc"
queries = {
    "Barack_Obama": {
        "req": "SELECT ?object WHERE {dbr:Barack_Obama rdfs:label ?object.}",
        "desc": "Get labels of Barack Obama",
    },
    "Michael_Jackson_songs": {
        "req": """
SELECT DISTINCT ?song ?songName ?releaseDate ?genre
WHERE {
    ?song a dbo:Song .
    ?song dbo:artist dbr:Michael_Jackson .
    ?song rdfs:label ?songName .
    
    OPTIONAL {
        ?song dbo:releaseDate ?releaseDate .
        ?song dbo:genre ?genre .
    }

    FILTER (lang(?songName) = "en")
}
LIMIT 100
}
""",
        "desc": "Get songs by Michael Jackson with optional release dates and genres",
    },
}
# dict for SPARQL request templates
# each key is a label, each value is a SPARQL query template with placeholders
templates = {
    "Artist_Albums": {
        "req": """
SELECT DISTINCT ?album_label ?release_date WHERE {{
    ?artist rdfs:label "{artist_name}"@en .
    ?album dbo:artist ?artist ;
            rdfs:label ?album_label ;
            dbo:releaseDate ?release_date .
    FILTER (lang(?album_label) = "en")
}}
ORDER BY DESC(?release_date)
LIMIT {limit}
    """,
        "desc": "Get N most recent albums of a specified artist with release dates",
    },
}


def get_predefined_query(q_label: str, pr_labels: list[str] | str = ["dbpedia"]) -> tuple[str, str]:
    """Retrieve a predefined SPARQL query by its label.
    Args:
        q_label (str): The label of the SPARQL query.
        pr_label (str): The prefix label to use.
    Returns:
        tuple: A tuple containing the description and the full SPARQL query string.
    """
    res = queries.get(q_label, None)
    if res is None:
        raise ValueError(f"No query found for label: {q_label}")
    
    if isinstance(pr_labels, str):
        assert pr_labels in prefixes or pr_labels == "all", f"Prefix label {pr_labels} not found."
        if pr_labels == "all":
            pr_labels = list(prefixes.keys())
        else:
            pr_labels = [pr_labels]
    elif isinstance(pr_labels, list):
        for l in pr_labels:
            assert l in prefixes, f"Prefix label {l} not found."
    else:
        raise ValueError("pr_labels must be a string or a list of strings.")

    return res["desc"], "\n".join([prefixes[l] for l in pr_labels]) + "\n" + res["req"]


def get_parametrized_query(t_label: str, pr_labels: list[str] = ["dbpedia"], **params) -> str:
    """Generate a SPARQL query by filling in the template with parameters.
    Args:
        t_label (str): label of the SPARQL template.
        pr_label (str): The prefix label to use.
        **params: Key-value pairs to fill in the placeholders in the template.
    Returns:
        tuple: A tuple containing the description the full SPARQL query string with parameters filled in.
    """
    template = templates.get(t_label, None)
    if template is None:
        raise ValueError(f"No template found for label: {t_label}")
    
    if isinstance(pr_labels, str):
        assert pr_labels in prefixes or pr_labels == "all", f"Prefix label {pr_labels} not found."
        if pr_labels == "all":
            pr_labels = list(prefixes.keys())
        else:
            pr_labels = [pr_labels]
    elif isinstance(pr_labels, list):
        for l in pr_labels:
            assert l in prefixes, f"Prefix label {l} not found."
    else:
        raise ValueError("pr_labels must be a string or a list of strings.")

    return template["desc"], "\n".join([prefixes[l] for l in pr_labels]) + "\n" + template["req"].format(**params)
