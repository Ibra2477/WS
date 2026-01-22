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
PREFIX hal: <http://data.archives-ouvertes.fr/schema/>
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

""",
        "desc": "Get songs by Michael Jackson with optional release dates and genres",
    },
    "Drake_songs_and_writers": {
        "req": """SELECT ?song ?songLabel (GROUP_CONCAT(DISTINCT ?writerLabel; separator=" | ") AS ?writers)
        WHERE {
            { <http://dbpedia.org/resource/Drake_(musician)> ^dbo:artist ?song . }
            UNION
            { <http://dbpedia.org/resource/Drake_(musician)> ^dbp:artist ?song . }

            { ?song dbo:writer ?writer . }
            UNION
            { ?song dbp:writer ?writer . }

            ?song rdfs:label ?songLabel .
            ?writer rdfs:label ?writerLabel .

            FILTER(lang(?songLabel) = "en")
            FILTER(lang(?writerLabel) = "en")
        }
        GROUP BY ?song ?songLabel
        LIMIT 20""",
        "desc": "Get songs by Drake with their writers"
    },
    "Recent_Albums_2010_plus": {
        "req": """SELECT DISTINCT ?album ?albumName ?Artist ?genre ?date ?title
        WHERE {
            ?album a dbo:Album .
            ?album rdfs:label ?albumName .
            ?album dbo:artist ?Artist .
            OPTIONAL {
                ?album dbo:genre ?genre .
                ?album dbo:releaseDate ?date .
                ?album dbp:title ?title .
            }
            FILTER (
                lang(?albumName) = "en" &&
                (!bound(?date) || ?date >= "2010-01-01"^^xsd:date)
            )
        }
        LIMIT 100
        """,
        "desc": "Get recent albums released after 2010"
    },
    "Music_Genres": {
        "req": """SELECT DISTINCT ?songName ?genreLabel
        WHERE {
            ?song a dbo:Song .
            ?song rdfs:label ?songName .
            OPTIONAL { ?song dbo:genre ?genre .
            ?genre rdfs:label ?genreLabel.  }
            FILTER(lang(?songName) = "en")
        }
        LIMIT 100
        
    """,
        "desc": "Get genres and names of songs",
    },
    "Non_US_Artists_And_Songs": {
        "req": """SELECT DISTINCT ?artist ?artistName ?song ?songName ?country
        WHERE {
            ?song a dbo:Song .
            ?song rdfs:label ?songName .
            ?song dbo:artist ?artist .

            ?artist a dbo:MusicalArtist .
            ?artist rdfs:label ?artistName .

            OPTIONAL { ?artist dbo:nationality ?country . }
            OPTIONAL { ?artist dbp:nationality ?country . }

            FILTER (
                lang(?songName) = "en" &&
                lang(?artistName) = "en" &&
                bound(?country) &&
                ?country != dbr:United_States
            )
        }
        LIMIT 100
    """,
        "desc": "Get non-US artists and their songs",
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
