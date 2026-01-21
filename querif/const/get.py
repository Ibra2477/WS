from .prefixes import prefixes
from .queries import queries
from .templates import templates

def list_queries() -> list[str]:
    """List all available predefined SPARQL query labels.
    Returns:
        list[str]: A list of predefined SPARQL query labels.
    """
    return list(queries.keys())


def list_templates() -> list[str]:
    """List all available SPARQL template labels.
    Returns:
        list[str]: A list of SPARQL template labels.
    """
    return list(templates.keys())


def get_query(q_label: str) -> tuple[str, str]:
    """Retrieve a predefined SPARQL query by its label.
    Args:
        q_label (str): The label of the SPARQL query.
        pr_label (str): The prefix label to use.
    Returns:
        tuple: A tuple containing the description and the full SPARQL query string.
    """
    res = queries.get(q_label, None)
    if res is None:
        raise ValueError(f"No query found for label: {q_label}")

    return res["desc"], prefixes + "\n" + res["req"]


def get_template(t_label: str,  **params) -> str:
    """Generate a SPARQL query by filling in the template with parameters.
    Args:
        t_label (str): label of the SPARQL template.
        pr_label (str): The prefix label to use.
        **params: Key-value pairs to fill in the placeholders in the template.
    Returns:
        tuple: A tuple containing the description the full SPARQL query string with parameters filled in.
    """
    template = templates.get(t_label, None)
    if template is None:
        raise ValueError(f"No template found for label: {t_label}")

    return template["desc"], prefixes + "\n" + template["req"].format(**params)
