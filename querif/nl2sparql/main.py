from .utils import _detect_query_type, QueryType
from .queries import *


def generate_and_execute_query(prompt: str, config_key: str = "LIRIS") -> tuple[str, dict] | tuple[None, None]:
    """Generate and execute a SPARQL query based on the user prompt.
    Args:
        prompt (str): The user prompt.
        config_key (str): The configuration key for the LLM client.
    Returns:
        tuple: The generated query and results, or (None, None) if failed.
    """
    query_type = _detect_query_type(prompt, config_key)
    print(f"Detected query type: {query_type.name}")

    handlers = {
        QueryType.FACT_LOOKUP: fact_lookup_query,
        QueryType.CLASS_QUERY: generate_class_query,
        QueryType.AGGREGATION: generate_aggregation_query,
        QueryType.COMPARISON: generate_comparison_query,
        QueryType.DEFINITION: generate_definition_query,
        QueryType.RELATIONSHIP: generate_relationship_query,
        QueryType.SUPERLATIVE: generate_superlative_query,
        QueryType.BOOLEAN: generate_boolean_query,
    }

    handler = handlers.get(query_type)
    if handler:
        return handler(prompt=prompt, config_key=config_key)

    return None, None
