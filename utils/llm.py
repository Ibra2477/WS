import openai
import os
import spacy
import requests

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

def parse_prompt(prompt: str) -> dict[str, str]:
    """Parse the prompt to extract the main question or task.
    Args:
        prompt (str): The full prompt.
    Returns:
        dict[str, str]: The constraints extracted from the prompt.
    """
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(prompt)

    nouns = [chunk.text for chunk in doc.noun_chunks]
    numbers = [ent.text for ent in doc.ents if ent.label_ == "CARDINAL"]

    comparators = []
    for token in doc:
        if token.text in [">", "more", "over", "greater"]:
            comparators.append(">")
        elif token.text in ["<", "less", "under"]:
            comparators.append("<")

    return {
        "nouns": nouns,
        "numbers": numbers,
        "comparators": comparators
    }


SPOTLIGHT_ENDPOINT = "https://api.dbpedia-spotlight.org/en/annotate"

def link_entities(text: str):
    headers = {"Accept": "application/json"}
    params = {"text": text, "confidence": 0.5}

    response = requests.get(
        SPOTLIGHT_ENDPOINT,
        headers=headers,
        params=params,
        timeout=10
    )


    entities = {}
    if response.status_code == 200:
        data = response.json()
    #     for r in data.get("Resources", []):
    #         surface = r["@surfaceForm"]
    #         uri = r["@URI"].replace("http://dbpedia.org/resource/", "dbr:")
    #         entities[surface] = uri

    # return entities
    return data

