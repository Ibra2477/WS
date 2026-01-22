import json
from ..utils import _check_response_is_empty, _create_client, _get_class_properties, _get_entities, _get_target_classes, _clean_sparql_response, configs
from ...const import prefixes
from ...execute import execute_query

class_query_prompt = """
You are a SPARQL expert for DBpedia.

Generate a SPARQL query to find instances of a class matching the user's criteria.

Rules:
- Use the provided target class as the main rdf:type
- Use the provided entities as constraints (e.g., dbo:country, dbo:birthPlace)
- Use the available properties for filtering and selection
- Include rdfs:label in SELECT with FILTER(lang(?label) = "en")
- Use OPTIONAL for properties that might not exist
- Add LIMIT 100 unless the question implies a specific count
- Return ONLY the SPARQL query, no explanations or markdown

Question: {question}

Target class: {target_class}

Known entities from question:
{entities}

Available data properties (numeric, dates, strings):
{data_properties}

Available object properties (relationships to other entities):
{object_properties}

Generate the SPARQL query:
"""


def generate_class_query(prompt: str, config_key: str = "LIRIS") -> tuple[str, dict] | tuple[None, None]:
    """Handle class-based queries to find instances matching criteria.

    Example: "Cities in France with population > 1M", "Movies directed by Spielberg"

    Args:
        prompt (str): The user prompt.
        config_key (str): The configuration key for the LLM client.
    Returns:
        tuple: The generated query and results.
    """
    entities = _get_entities(prompt)
    print("Entities:", entities)
    target_classes = _get_target_classes(prompt, n_class=3, config_key=config_key)
    print("Target classes:", target_classes)

    config = configs.get(config_key)
    client = _create_client(prefix=config["prefix"])

    for target_class in target_classes:
        props = _get_class_properties(target_class)
        print("Props of t. class", props)

        user_content = class_query_prompt.format(
            question=prompt,
            target_class=target_class,
            entities=json.dumps(entities),
            data_properties=", ".join(props["data"][:15]),
            object_properties=", ".join(props["object"][:15]),
        )

        response = client.chat.completions.create(
            model=config["model"],
            messages=[{"role": "user", "content": user_content}],
            temperature=config["temperature"],
        )

        query = _clean_sparql_response(response.choices[0].message.content)
        print("Generated query:")
        print(query)

        try:
            results = execute_query(prefixes + query)
            if not _check_response_is_empty(results):
                return query, results
        except Exception as e:
            print(f"Query execution failed for class {target_class}: {e}")
            continue

    return None, None
