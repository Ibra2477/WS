from ..utils import _get_entities
from ...const import prefixes
from ...execute import execute_query


def generate_relationship_query(prompt: str) -> tuple[str, dict] | tuple[None, None]:
    """Handle relationship queries between entities.
    Args:
        prompt (str): The user prompt.
        config_key (str): The configuration key for the LLM client.
    Returns:
        tuple: The generated query and results.
    """
    entities = _get_entities(prompt)

    if len(entities) < 2:
        return None, None

    entity_list = list(entities.values())
    entity1, entity2 = entity_list[0], entity_list[1]

    # Find direct relationships
    query = f"""
    SELECT ?predicate ?direction WHERE {{
        {{
            {entity1} ?predicate {entity2} .
            BIND("forward" AS ?direction)
        }}
        UNION
        {{
            {entity2} ?predicate {entity1} .
            BIND("reverse" AS ?direction)
        }}
    }}
    """

    results = execute_query(prefixes + query)
    return query, results