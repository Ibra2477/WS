import json
from ..utils import (
    _check_response_is_empty,
    _create_client,
    _get_entities,
    _clean_sparql_response,
    _get_common_properties,
    _get_entity_properties,
    configs,
)
from ...const import prefixes
from ...execute import execute_query

comparison_prompt = """
You are a SPARQL expert for DBpedia.

Generate a SPARQL query to compare two or more entities.

Rules:
- Select the relevant property values for each entity
- Use the entities provided in the question
- Include rdfs:label for each entity with FILTER(lang(?label) = "en")
- For "who is older" use dbo:birthDate (older = earlier date)
- For "which is larger" use dbo:populationTotal or dbo:area
- Return values that allow comparison (dates, numbers)
- Order results to show the comparison clearly
- Return ONLY the SPARQL query, no explanations or markdown

Question: {question}

Entities to compare:
{entities}

Available common properties:
{properties}

Generate the SPARQL query:
"""


def generate_comparison_query(prompt: str, config_key: str = "LIRIS") -> tuple[str, dict] | tuple[None, None]:
    """Handle comparison queries between two or more entities.

    Example: "Who is older, Obama or Trump?", "Which city is larger, Paris or London?"

    Args:
        prompt (str): The user prompt.
        config_key (str): The configuration key for the LLM client.
    Returns:
        tuple: The generated query and results.
    """
    entities = _get_entities(prompt)

    if len(entities) < 2:
        # Try to find at least 2 entities
        return None, None

    entity_uris = list(entities.values())

    # Get common properties between entities
    common_props = _get_common_properties(entity_uris[:2], limit=20)

    if not common_props:
        # Fallback: get properties from first entity
        props = _get_entity_properties(entity_uris[0], limit=20)
        common_props = [p["property"] for p in props]

    props_str = "\n".join([f"  {p}" for p in common_props])

    config = configs.get(config_key)
    client = _create_client(prefix=config["prefix"])

    user_content = comparison_prompt.format(
        question=prompt,
        entities=json.dumps(entities),
        properties=props_str,
    )

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
        print(f"Comparison query execution failed: {e}")

    return None, None
