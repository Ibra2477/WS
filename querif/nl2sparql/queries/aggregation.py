from ..utils import (
    _check_response_is_empty,
    _create_client,
    _get_class_properties,
    _get_target_classes,
    _clean_sparql_response,
    configs,
)
from ...const import prefixes
from ...execute import execute_query
from pprint import pprint

aggregation_prompt = """
You are a SPARQL expert for DBpedia.

Generate a SPARQL query to perform aggregation operations (COUNT, SUM, AVG, MAX, MIN).

Rules:
- Use COUNT for counting instances
- Use SUM/AVG/MAX/MIN for numeric properties
- Use GROUP BY when aggregating by categories
- Filter results appropriately
- Return ONLY the SPARQL query, no explanations or markdown

Question: {question}

Target class: {target_class}

Available properties:
{properties}

Generate the SPARQL query:
"""


def generate_aggregation_query(prompt: str, config_key: str = "LIRIS") -> tuple[str, dict] | tuple[None, None]:
    """Handle aggregation queries (COUNT, SUM, AVG, etc.).

    Example: "How many albums did Adele release?", "Count cities in Germany"

    Args:
        prompt (str): The user prompt.
        config_key (str): The configuration key for the LLM client.
    Returns:
        tuple: The generated query and results.
    """
    target_classes = _get_target_classes(prompt, n_class=1, config_key=config_key)

    target_class = target_classes[0] if target_classes else "owl:Thing"

    class_props = _get_class_properties(target_class)
    props_str = "\n".join([f"  {p}" for p in class_props["data"] + class_props["object"]])

    config = configs.get(config_key)
    client = _create_client(prefix=config["prefix"])

    user_content = aggregation_prompt.format(
        question=prompt,
        target_class=target_class,
        properties=props_str,
    )

    print("Resulting prompt:")
    pprint(user_content)
    print()

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
        print(f"Aggregation query execution failed: {e}")

    return None, None
