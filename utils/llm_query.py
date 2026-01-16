import openai
import os

ollama_system_prompt = """
You are a helpful assistant that generates SPARQL queries.
You output only the SPARQL query without any additional text.
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


def _create_llm_client():
    base_url = os.getenv("LLM_API")
    api_key = os.getenv("LLM_API_KEY")
    if not base_url or not api_key:
        raise ValueError("LLM_API and LLM_API_KEY must be set in environment variables.")
    client = openai.OpenAI(base_url=base_url, api_key=api_key)
    return client


def create_ollama_query(prompt: str, model: str = "llama3:70b") -> str:
    """Create a query using Ollama LLM.
    Args:
        prompt (str): The prompt to send to the LLM.
        model (str): The model to use.
    Returns:
        str: The generated query from the LLM.
    """
    client = _create_llm_client()
    response = client.chat.completions.create(
        model=model, messages=[{"role": "system", "content": ollama_system_prompt}, {"role": "user", "content": prompt}], temperature=0.4
    )
    return response.choices[0].message.content
