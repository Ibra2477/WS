# Namespace mappings
namespaces = {
    # Core RDF/OWL
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    # DBpedia specific
    "dbr": "http://dbpedia.org/resource/",
    "dbo": "http://dbpedia.org/ontology/",
    "dbp": "http://dbpedia.org/property/",
    "dbc": "http://dbpedia.org/resource/Category:",
    "dbt": "http://dbpedia.org/resource/Template:",
    # Common external vocabularies
    "foaf": "http://xmlns.com/foaf/0.1/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
    "georss": "http://www.georss.org/georss/",
    "prov": "http://www.w3.org/ns/prov#",
    # Links to other datasets
    "wikidata": "http://www.wikidata.org/entity/",
    "schema": "http://schema.org/",
}

# Reverse mapping: full URI -> prefix
namespaces_rev = {v: k for k, v in namespaces.items()}

# Generate SPARQL PREFIX declarations from namespaces
prefixes = "\n".join([f"PREFIX {prefix}: <{uri}>" for prefix, uri in namespaces.items()]) + "\n"


def uri_to_prefixed(uri: str) -> str:
    """Convert a full URI to prefixed format.
    Args:
        uri (str): The full URI (e.g., "http://dbpedia.org/ontology/birthDate").
    Returns:
        str: The prefixed URI (e.g., "dbo:birthDate").
    """
    for full_uri, prefix in namespaces_rev.items():
        if uri.startswith(full_uri):
            local_name = uri[len(full_uri) :]
            return f"{prefix}:{local_name}"
    return uri  # Return as-is if no match


def prefixed_to_uri(prefixed: str) -> str:
    """Convert a prefixed URI to full URI format.
    Args:
        prefixed (str): The prefixed URI (e.g., "dbo:birthDate").
    Returns:
        str: The full URI (e.g., "http://dbpedia.org/ontology/birthDate").
    """
    if ":" in prefixed:
        prefix, local_name = prefixed.split(":", 1)
        if prefix in namespaces:
            return namespaces[prefix] + local_name
    return prefixed  # Return as-is if no match
