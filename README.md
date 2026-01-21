# `querIF`

A Python package to simplify querying DBpedia.

#### Features
- Natural language to SPARQL translation
- Results clustering and visualization
- Pre-built music query templates

#### Get Started
*For Users:*
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install git+https://github.com/Ibra2477/WS.git
```

*For Development:*
```bash
git clone https://github.com/Ibra2477/WS
cd WS
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

#### Usage
If you want use llms first enter your api keys to .env (consult env.template for intended format)

Now you can run the frontend app with:
```bash
querif run app
```

