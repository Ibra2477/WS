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