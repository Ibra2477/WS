from ..utils import _create_client, _get_entities, _clean_sparql_response, configs
from ...const import prefixes
from ...execute import execute_query

boolean_prompt = """
You are a SPARQL expert for DBpedia.

Generate a SPARQL ASK query to answer a yes/no question.

Rules:
- Use ASK {{ }} syntax
- Return true if the pattern exists
- Return ONLY the SPARQL query, no explanations

Question: {question}

Entities: {entities}

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

    config = configs.get(config_key)
    client = _create_client(prefix=config["prefix"])

    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": boolean_prompt.format(question=prompt, entities=list(entities.values()))},
            {"role": "user", "content": prompt},
        ],
        temperature=config["temperature"],
    )

    query = _clean_sparql_response(response.choices[0].message.content)
    results = execute_query(prefixes + query)
    return query, results
