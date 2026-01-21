from ..utils import (
    _create_client,
    configs,
    _get_entities,
    _get_entity_properties,
    _clean_sparql_response,
    _check_response_is_empty,
)
from ...execute import execute_query
from ...const import prefixes


fact_lookup_prompt = """
You are a SPARQL expert for DBpedia.

Generate a SPARQL query to retrieve a specific fact about an entity.

Rules:
- Select the most relevant property values from the available properties
- Use FILTER with language tags for string values (usually @en)
- Handle optional properties gracefully
- Return ONLY the SPARQL query, no explanations or markdown

Question: {question}

Entity: {entity}

Available properties on this entity:
{properties}

Generate the SPARQL query:
"""


def fact_lookup_query(prompt: str, config_key: str = "LIRIS") -> tuple[str, dict] | tuple[None, None]:
    """Handle fact lookup queries about specific entities.

    Example: "When was Obama born?", "What is the capital of France?"

    Args:
        prompt (str): The user prompt.
        config_key (str): The configuration key for the LLM client.
    Returns:
        tuple: The generated query and results.
    """
    entities = _get_entities(prompt)

    if not entities:
        raise ValueError("No entities found in the prompt for fact lookup query.")

    # Get the main entity (first one found)
    main_entity = list(entities.values())[0]
    props = _get_entity_properties(main_entity, limit=30)

    if not props:
        raise ValueError("No properties found for the main entity in fact lookup query.")

    # Format properties for prompt
    props_str = "\n".join([f"  {p['property']}: {p['value']}" for p in props])

    config = configs.get(config_key)
    client = _create_client(prefix=config["prefix"])

    user_content = fact_lookup_prompt.format(question=prompt, entity=main_entity, properties=props_str)

    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "user", "content": user_content}],
        temperature=config["temperature"],
    )

    query = _clean_sparql_response(response.choices[0].message.content)

    try:
        results = execute_query(prefixes + query)
        if not _check_response_is_empty(results):
            return query, results
    except Exception as e:
        print(f"Query execution failed: {e}")

    return None, None
