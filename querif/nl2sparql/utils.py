import openai
import os
import requests
from enum import Enum
from ..const import prefixes, uri_to_prefixed
from ..execute import execute_query
import warnings

configs = {
    "LIRIS": {
        "prefix": "LIRIS",
        "model": "llama3:70b",
        "temperature": 0.4,
    },
    "DEEPSEEK": {
        "prefix": "DEEPSEEK",
        "model": "deepseek-chat",
        "temperature": 0.4,
    },
}

#8 catégories de questions
query_type_detection_prompt = """
Classify the user's question into exactly ONE category:

- FACT_LOOKUP: Asking for a specific property of a named entity
  Examples: "When was Obama born?", "How long was WW2?", "What is the capital of France?"

- CLASS_QUERY: Asking for a list of things matching criteria
  Examples: "Cities in France with population > 1M", "Movies directed by Spielberg"

- AGGREGATION: Asking for counts, sums, or statistics
  Examples: "How many albums did Adele release?", "Total population of EU countries"

- COMPARISON: Comparing two or more entities
  Examples: "Who is older, Obama or Trump?", "Which city is larger, Paris or London?"

- DEFINITION: Asking what something or someone is
  Examples: "What is DBpedia?", "Who is Albert Einstein?", "What is the Eiffel Tower?"

- RELATIONSHIP: Finding how entities are connected
  Examples: "How are Obama and Biden related?", "What connects Apple and Steve Jobs?"

- SUPERLATIVE: Asking for extremes (largest, oldest, most, etc.)
  Examples: "Largest city in Germany", "Oldest university in the world", "Most populated country"

- BOOLEAN: Yes/no questions
  Examples: "Is Paris the capital of France?", "Did Einstein win a Nobel Prize?"

Reply with ONLY the category name in uppercase, nothing else.
"""

target_class_detection_prompt = """
You are an expert in DBpedia ontology and SPARQL.
Your task is to identify the most relevant DBpedia classes for a user's query.

Instructions:
- Analyze the user prompt to understand the main entities and concepts
- Return ONLY {n_class} DBpedia class URIs (e.g., dbo:City, dbo:Person, dbo:Film)
- Order them by relevance (most relevant first)
- Separate each URI with a single space
- Do NOT include explanations, prefixes beyond "dbo:", or any additional text

Example format: dbo:City dbo:Place dbo:Region dbo:PopulatedPlace
"""

EXCLUDED_NAMESPACES = [
    "http://www.w3.org/2002/07/owl#",  # owl:sameAs, etc.
    "http://www.w3.org/ns/prov#",  # provenance data
    "http://dbpedia.org/resource/Template:",  # templates
    "http://www.wikidata.org/entity/",  # wikidata IDs
    "http://purl.org/linguistics/gold/",  # linguistic data
]


class QueryType(Enum):
    """Types of SPARQL queries supported by the system."""

    FACT_LOOKUP = "fact_lookup"  # Direct property of an entity
    CLASS_QUERY = "class_query"  # Find instances of a class
    AGGREGATION = "aggregation"  # COUNT, SUM, AVG, etc.
    COMPARISON = "comparison"  # Compare two entities
    DEFINITION = "definition"  # Define a term or concept
    RELATIONSHIP = "relationship"  # Relationship between entities
    SUPERLATIVE = "superlative"  # Superlative queries (e.g., largest, smallest)
    BOOLEAN = "boolean"  # True/False questions


def _create_client(prefix: str) -> openai.OpenAI:
    """Create and return an openai client using environment variables.
    Args:
        prefix (str): The prefix for the environment variables.
    Returns:
        openai.OpenAI: The configured OpenAI client.
    """
    base_url = os.getenv(f"{prefix}_API")
    api_key = os.getenv(f"{prefix}_API_KEY")
    if not base_url or not api_key:
        raise ValueError(f"{prefix}_API and {prefix}_API_KEY must be set in environment variables.")
    client = openai.OpenAI(base_url=base_url, api_key=api_key)
    return client


def _get_entities(text: str, confidence: int = 0.3) -> dict[str, str]:
    """Find DBpedia resources in the given text using DBpedia Spotlight.
    Args:
        text (str): The input text. (prompt of the user)
        confidence (int): The confidence threshold for entity recognition.
    Returns:
        dict[str, str]: A dictionary mapping surface forms to DBpedia resource URIs.
    """
    headers = {"Accept": "application/json"}
    params = {"text": text, "confidence": confidence}
    response = requests.get("https://api.dbpedia-spotlight.org/en/annotate", headers=headers, params=params, timeout=10)

    entities = {}
    if response.status_code == 200:
        data = response.json()
        for r in data.get("Resources", []):
            surface = r["@surfaceForm"]
            uri = r["@URI"].replace("http://dbpedia.org/resource/", "dbr:")
            entities[surface] = uri
    else:
        raise ValueError(f"DBpedia Spotlight request failed with status code {response.status_code}")

    return entities


def _get_target_classes(prompt: str, n_class: int = 5, config_key: str = "LIRIS") -> list[str]:
    """Get target DBpedia classes for the given prompt using LLM.
    Args:
        prompt (str): The user prompt.
        n_class (int): Number of classes to return.
        config_key (str): The configuration key for the LLM client.
    Returns:
        list[str]: A list of verified target class URIs.
    """
    config = configs.get(config_key, None)
    if config is None:
        raise ValueError(f"No configuration found for key: {config_key}")
    client = _create_client(prefix=config["prefix"])

    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "system", "content": target_class_detection_prompt.format(n_class=n_class)}, {"role": "user", "content": prompt}],
        temperature=config["temperature"],
    )

    classes_str = response.choices[0].message.content
    classes = classes_str.strip().split()

    # Verify classes exist in DBpedia
    verified_classes = _verify_classes_exist(classes)

    if not verified_classes:
        warnings.warn(f"No valid DBpedia classes found for prompt: {prompt}", UserWarning)

    return verified_classes


def _verify_classes_exist(classes: list[str]) -> list[str]:
    """Verify which classes actually exist in DBpedia ontology.
    Args:
        classes (list[str]): List of class URIs (e.g., ["dbo:City", "dbo:Person"]).
    Returns:
        list[str]: List of classes that exist in DBpedia.
    """
    if not classes:
        return []

    values_clause = " ".join(f"({c})" for c in classes)
    #Construit une requete sparql qui vérifie si les classes sont de type owl:Class
    query = f"""
    SELECT DISTINCT ?class WHERE {{
        VALUES (?class) {{ {values_clause} }}
        ?class rdf:type owl:Class .
    }}
    """

    try:
        results = execute_query(prefixes + query)
        existing = [uri_to_prefixed(r["class"]["value"]) for r in results["results"]["bindings"]]

        # Preserve original order
        return [c for c in classes if c in existing]
    except Exception as e:
        warnings.warn(f"Failed to verify classes: {e}", RuntimeWarning)
        return classes  # Return unverified if query fails


def _verify_class_has_instances(class_uri: str) -> bool:
    """Check if a class has any instances in DBpedia.
    Args:
        class_uri (str): The URI of the class (e.g., "dbo:City").
    Returns:
        bool: True if class has instances, False otherwise.
    """
    query = f"""
    ASK {{
        ?s rdf:type {class_uri} .
    }}
    """

    try:
        results = execute_query(prefixes + query)
        return results.get("boolean", False)
    except Exception:
        return True  # Assume exists if query fails

# Récupère 2 types de propriétés (datatype et object) pour une classe donnée
def _get_class_properties_ont(class_uri: str, property_type: str) -> list[str]:
    """Query DBpedia Ontology for properties of a given type associated with a class.
    Args:
        class_uri (str): The URI of the class (e.g., "dbo:City").
        property_type (str): The OWL property type to query for
            (e.g., "owl:DatatypeProperty" or "owl:ObjectProperty").
    Returns:
        list[str]: A list of property URIs in prefixed format (e.g., ["dbo:population", "dbo:name"]).
    """
    query = f"""
    SELECT DISTINCT ?property
    WHERE {{
        ?property rdf:type {property_type} ;
                  rdfs:domain {class_uri} .
    }}
    """
    results = execute_query(prefixes + query)
    return [uri_to_prefixed(r["property"]["value"]) for r in results["results"]["bindings"]]


def _get_class_properties(class_uri: str, verify: bool = True) -> dict[str, list[str]]:
    """Discover properties of a given class in DBpedia.
    Args:
        class_uri (str): The URI of the class (e.g., "dbo:City").
        verify (bool): If True, verify properties are actually used in DBpedia.
    Returns:
        dict[str, list[str]]: A dictionary with "data" and "object" property lists.
    """
    data_props = _get_class_properties_ont(class_uri, "owl:DatatypeProperty")
    object_props = _get_class_properties_ont(class_uri, "owl:ObjectProperty")

    if not verify:
        return {
            "data": data_props[:20],
            "object": object_props[:20],
        }

    # Verify properties in a single query
    verified_data = _verify_properties_batch(class_uri, data_props[:20])
    verified_object = _verify_properties_batch(class_uri, object_props[:20])

    return {
        "data": verified_data,
        "object": verified_object,
    }


def _verify_properties_batch(class_uri: str, properties: list[str]) -> list[str]:
    """Verify which properties found in ontology are actually used for a class in a single query.
    Args:
        class_uri (str): The URI of the class (e.g., "dbo:City").
        properties (list[str]): List of property URIs to check.
    Returns:
        list[str]: List of properties that are actually used.
    """
    if not properties:
        return []

    values_clause = " ".join(f"({p})" for p in properties)

    query = f"""
    SELECT DISTINCT ?property WHERE {{
        VALUES (?property) {{ {values_clause} }}
        ?s rdf:type {class_uri} ;
           ?property ?o .
    }}
    """

    try:
        results = execute_query(prefixes + query)
        return [uri_to_prefixed(r["property"]["value"]) for r in results["results"]["bindings"]]
    except Exception as e:
        warnings.warn(f"Failed to verify properties for {class_uri}: {e}", RuntimeWarning)
        return properties  # Return unverified if query fails


def _detect_query_type(prompt: str, config_key: str = "LIRIS") -> QueryType:
    """Detect the type of query from the user prompt.
    Args:
        prompt (str): The user prompt.
        config_key (str): The configuration key for the LLM client.
    Returns:
        QueryType: The detected query type.
    """
    config = configs.get(config_key)
    if config is None:
        raise ValueError(f"No configuration found for key: {config_key}")
    client = _create_client(prefix=config["prefix"])

    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "system", "content": query_type_detection_prompt}, {"role": "user", "content": prompt}],
        temperature=0.1,
    )

    type_str = response.choices[0].message.content.strip().upper()

    type_mapping = {
        "FACT_LOOKUP": QueryType.FACT_LOOKUP,
        "CLASS_QUERY": QueryType.CLASS_QUERY,
        "AGGREGATION": QueryType.AGGREGATION,
        "COMPARISON": QueryType.COMPARISON,
        "DEFINITION": QueryType.DEFINITION,
        "RELATIONSHIP": QueryType.RELATIONSHIP,
        "SUPERLATIVE": QueryType.SUPERLATIVE,
        "BOOLEAN": QueryType.BOOLEAN,
    }

    return type_mapping.get(type_str, QueryType.CLASS_QUERY)


def _get_entity_properties(entity_uri: str, limit: int = 30) -> list[dict]:
    """Get properties and sample values for a given entity.
    Args:
        entity_uri (str): The entity URI (e.g., "dbr:World_War_II").
        limit (int): Maximum number of properties to return.
    Returns:
        list[dict]: List of property-value pairs.
    """
    # Build FILTER to exclude noisy namespaces
    exclusion_filters = " && ".join([f'!STRSTARTS(STR(?property), "{uri}")' for uri in EXCLUDED_NAMESPACES])

    query = f"""
    SELECT DISTINCT ?property ?value WHERE {{
        {entity_uri} ?property ?value .
        FILTER({exclusion_filters})
    }} LIMIT {limit}
    """
    results = execute_query(prefixes + query)

    props = []
    for r in results["results"]["bindings"]:
        prop_name = uri_to_prefixed(r["property"]["value"])
        value = r["value"]["value"]
        if len(str(value)) > 100:
            value = str(value)[:100] + "..."
        props.append({"property": prop_name, "value": value})

    return props


def _get_common_properties(entity_uris: list[str], limit: int = 20) -> list[str]:
    """Get properties that are common to multiple entities.
    Args:
        entity_uris (list[str]): List of entity URIs.
        limit (int): Maximum number of properties to return.
    Returns:
        list[str]: List of common property URIs.
    """
    if len(entity_uris) < 2:
        return []

    exclusion_filters = " && ".join([f'!STRSTARTS(STR(?property), "{uri}")' for uri in EXCLUDED_NAMESPACES])

    entity1, entity2 = entity_uris[0], entity_uris[1]
    query = f"""
    SELECT DISTINCT ?property WHERE {{
        {entity1} ?property ?val1 .
        {entity2} ?property ?val2 .
        FILTER({exclusion_filters})
    }} LIMIT {limit}
    """
    results = execute_query(prefixes + query)

    return [uri_to_prefixed(r["property"]["value"]) for r in results["results"]["bindings"]]

# enlève les blocs maarkdown que le llm peut ajouter
def _clean_sparql_response(response: str) -> str:
    """Clean LLM response to extract pure SPARQL query.
    Args:
        response (str): The raw LLM response.
    Returns:
        str: Clean SPARQL query.
    """
    query = response.strip()
    # Remove markdown code blocks
    query = query.replace("```sparql", "").replace("```sql", "").replace("```", "")
    return query.strip()


def _check_response_is_empty(response: dict) -> bool:
    """Check if DBpedia response is empty.
    Args:
        response (dict): The response from DBpedia.
    Returns:
        bool: True if response is empty, False otherwise.
    """
    if "results" in response:
        if "bindings" in response["results"]:
            if len(response["results"]["bindings"]) == 0:
                return True
    return False
