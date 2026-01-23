from ..utils import _create_client, _get_entities, _clean_sparql_response, configs, _get_entity_properties
from ...const import prefixes
from ...execute import execute_query
from pprint import pprint

boolean_prompt = """
You are a SPARQL expert for DBpedia.

Generate a SPARQL ASK query to answer a yes/no question.

Rules:
- Use ASK {{ }} syntax
- Return true if the pattern exists
- Return ONLY the SPARQL query, no explanations

Question: {question}

Entities and their properties: {entities_end_properties}

Generate the SPARQL query:
"""


def generate_boolean_query(prompt: str, config_key: str = "LIRIS") -> tuple[str, dict] | tuple[None, None]:
    """Handle yes/no questions using ASK queries.
    Args:
        prompt (str): The user prompt.
        config_key (str): The configuration key for the LLM client.
    Returns:
        tuple: The generated query and results.
    """
    entities = _get_entities(prompt)

    print("Generating boolean query for prompt:", prompt)
    print("Identified entities:")
    pprint(entities)
    print()

    ent_and_props = {}

    for ent_uri in entities.values():
        print("Fetching properties for entity:", ent_uri)
        props = _get_entity_properties(ent_uri, limit=30)
        print("Properties found:")
        pprint(props)
        print()
        ent_and_props[ent_uri] = props


    print("Resulting prompt:")
    pprint(boolean_prompt.format(question=prompt, entities_end_properties=ent_and_props))

    config = configs.get(config_key)
    client = _create_client(prefix=config["prefix"])

    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": boolean_prompt.format(question=prompt, entities_end_properties=ent_and_props)},
            {"role": "user", "content": prompt},
        ],
        temperature=config["temperature"],
    )

    query = _clean_sparql_response(response.choices[0].message.content)

    print("Generated SPARQL query:")
    pprint(query)
    print()

    results = execute_query(prefixes + query)
    return query, results
