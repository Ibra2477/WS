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
    "Recent_Albums_2010_plus": {
        "req": """
SELECT DISTINCT ?album ?albumName ?Artist ?genre ?date ?title
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
        "desc": "Get recent albums released after 2010",
    },
    "Music_Genres": {
        "req": """
SELECT DISTINCT ?songName ?genreLabel
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
        "req": """
SELECT DISTINCT ?artist ?artistName ?song ?songName ?country
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
