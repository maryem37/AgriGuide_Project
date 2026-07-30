# Agent de Régulation Agricole

Premier agent d'une plateforme multi-agents pour l'agriculture. Il permet de :

1. Répondre aux questions de réglementation agricole via un **RAG hybride**
   (embeddings denses + BM25).
2. Rechercher de nouvelles aides financières ou procédures via le web.
3. Remplir des formulaires / documents à partir des informations fournies.
4. Réviser des documents (relecture, cohérence, conformité).

## Stack technique

- Python 3.11+
- FastAPI
- LangChain
- Qdrant (vector store)
- Embeddings Mistral (`mistral-embed`)
- BM25 (recherche par mots-clés)

## Structure du projet

```
app/
├── main.py              # point d'entrée FastAPI
├── config/              # configuration (variables d'environnement)
├── api/                 # routes FastAPI
├── agent/               # orchestration de l'agent (LangChain)
├── tools/               # outils de l'agent (RAG, recherche web, formulaires, révision)
├── services/             # services internes (Qdrant, embeddings, BM25, retriever hybride)
├── schemas/              # modèles Pydantic (requêtes/réponses)
└── prompts/              # templates de prompts
data/
└── vectorstore/          # données du vector store (ignoré par git)
tests/                    # tests
```

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

pip install -r requirements.txt
cp .env.example .env           # puis renseigner les clés/valeurs
```

## Lancement

```bash
uvicorn app.main:app --reload
```

L'API est ensuite disponible sur http://localhost:8000 (voir `/health` pour vérifier le statut).
