from setuptools import setup, find_packages

setup(
    name="querif",
    version="0.1.0",
    description="A Python package to simplify querying DBpedia.",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "networkx",
        "SPARQLWrapper",
        "openai",
        "sentence-transformers",
        "plotly",
        "streamlit",
        "watchdog",
        "python-dotenv",
        "umap-learn"
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "querif=querif.app.run_app:main",
        ],
    },
)
