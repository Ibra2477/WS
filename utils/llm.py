import openai
import os

llm_system_prompt = """
You are a helpful assistant that generates SPARQL queries.
You output only the SPARQL query without any additional text.
You have to generate a query for {source}.

You follow the SPARQL syntax strictly:
Global Structure of a SPARQL Query (Headings/Sections):
PREFIX – define namespaces
SELECT – specify variables to retrieve
WHERE – define patterns and constraints
FILTER – apply conditions on variables
GROUP BY / HAVING – aggregate data when needed
ORDER BY – sort results
LIMIT / OFFSET – restrict number of results

General Advice:
Always use PREFIX to make URIs readable.
Use FILTER for conditions like birthdate checks.
Use GROUP BY + HAVING for counts (like minimum number of albums).
Limit results during testing to avoid overloading endpoints.
Use meaningful variable names for clarity.
"""

configs = {
    "LIRIS": {
        "prefix": "LIRIS",
        "model": "llama3:70b",
        "temperature": 0.4,
    },
    "DEEPSEEK": {
        "prefix": "DEEPSEEK",
        "model": "deepseek-reasoner",
        "temperature": 0.4,
    },
}


def _create_client(prefix: str) -> openai.OpenAI:
    """Create and return an openai client using environment variables."""
    base_url = os.getenv(f"{prefix}_API")
    api_key = os.getenv(f"{prefix}_API_KEY")
    if not base_url or not api_key:
        raise ValueError(f"{prefix}_API and {prefix}_API_KEY must be set in environment variables.")
    client = openai.OpenAI(base_url=base_url, api_key=api_key)
    return client


def create_query(prompt: str, config_key: str = "LIRIS") -> str:
    """Create a query using Ollama LLM.
    Args:
        prompt (str): The prompt to send to the LLM.
        model (str): The model to use.
    Returns:
        str: The generated query from the LLM.
    """
    config = configs.get(config_key, None)
    if config is None:
        raise ValueError(f"No configuration found for key: {config_key}")
    client = _create_client(prefix=config["prefix"])
    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "system", "content": llm_system_prompt}, {"role": "user", "content": prompt}],
        temperature=config["temperature"],
    )
    return response.choices[0].message.content
