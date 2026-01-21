from ..utils import _get_entities
from ...const import prefixes
from ...execute import execute_query

def generate_definition_query(prompt: str) -> tuple[str, dict] | tuple[None, None]:
    """Handle definition queries like 'What is X?' or 'Who is Y?'.
    Args:
        prompt (str): The user prompt.
        config_key (str): The configuration key for the LLM client.
    Returns:
        tuple: The generated query and results.
    """
    entities = _get_entities(prompt)

    if not entities:
        return None, None

    main_entity = list(entities.values())[0]

    query = f"""
    SELECT ?label ?abstract ?type WHERE {{
        {main_entity} rdfs:label ?label ;
                      dbo:abstract ?abstract .
        OPTIONAL {{ {main_entity} rdf:type ?type . }}
        FILTER (lang(?label) = "en" && lang(?abstract) = "en")
    }} LIMIT 1
    """

    results = execute_query(prefixes + query)
    return query, results