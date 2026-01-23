from ..utils import _create_client, _get_class_properties, _get_entities, _get_target_classes, _clean_sparql_response, configs
from ...const import prefixes
from ...execute import execute_query
from pprint import pprint


superlative_prompt = """
You are a SPARQL expert for DBpedia.

Generate a SPARQL query to find the extreme value (max, min, largest, oldest, etc.).

Rules:
- Use ORDER BY DESC/ASC with LIMIT 1
- Select the relevant numeric/date property
- Return ONLY the SPARQL query, no explanations

Question: {question}

Target class: {target_class}

Available properties:
{properties}

Generate the SPARQL query:
"""


def generate_superlative_query(prompt: str, config_key: str = "LIRIS") -> tuple[str, dict] | tuple[None, None]:
    """Handle superlative queries (largest, oldest, most, etc.).
    Args:
        prompt (str): The user prompt.
        config_key (str): The configuration key for the LLM client.
    Returns:
        tuple: The generated query and results.
    """
    target_classes = _get_target_classes(prompt, n_class=1, config_key=config_key)
    print("Identified target classes:", target_classes, "\n")

    if not target_classes:
        return None, None

    target_class = target_classes[0]
    all_props = _get_class_properties(target_class)
    print("Available properties for class:")
    pprint(all_props)
    print()


    config = configs.get(config_key)
    client = _create_client(prefix=config["prefix"])

    print("Resulting prompt:")
    pprint(superlative_prompt.format(question=prompt, target_class=target_class, properties="\n".join(all_props)))

    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {
                "role": "system",
                "content": superlative_prompt.format(question=prompt, target_class=target_class, properties="\n".join(all_props)),
            },
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
