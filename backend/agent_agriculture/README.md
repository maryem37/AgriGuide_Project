# Agent Agriculture

**Rôle** : analyser un terrain (géo/sol/climat) et recommander les 5 meilleures
cultures.

## Réutilise le projet existant

Ce module reprend directement le pipeline développé dans le prototype
autonome `agri-advisor-parcelle` (FastAPI + React), migré ici dans la
structure du monorepo (`backend/agent_agriculture`, données persistées dans
`database/schema.sql`, UI intégrée à `frontend/src/routes/agriculture.tsx`
plutôt que dans un frontend séparé). Le prototype d'origine a été supprimé une
fois cette migration terminée.

Pipeline : résout une parcelle (cadastre/RPG) -> interroge en parallèle
Sentinel-2 (NDVI), SoilGrids (sol), Open-Meteo (météo), et un classifieur DL
optionnel (TempCNN) -> calcule le top 5 des cultures + besoins
azote/irrigation avec des formules explicites (pas le LLM) -> génère un
rapport français grounded via RAG (Chroma + Mistral) en deux étapes avec audit
anti-hallucination.

## Entrée

- `terrain_id` (géométrie déjà enregistrée dans `terrains`, créée par le
  service `auth` à l'inscription ou via `POST /auth/me/terrains`), **ou**
- un point cliqué sur la carte (`point`), résolu en direct contre le
  cadastre/RPG — permet d'explorer une parcelle précise sans l'avoir
  préalablement déclarée comme terrain.

## Sortie

- Retournée directement dans la réponse HTTP (`POST /agriculture/analyze`),
  et — si `terrain_id` est fourni — écrite en base :
  - `land_profiles` : sol, satellite, RPG, climat
  - `crop_recommendations` : top 5 cultures avec score + besoins
    (pesticides, engrais, irrigation) + `feature_importance` pour
    l'explicabilité

## Endpoints

| Méthode | Route                          | Description                                                                 |
|---------|---------------------------------|-------------------------------------------------------------------------------|
| POST    | `/agriculture/parcel/resolve`   | Résout un point GPS en parcelle cadastrale/RPG (aperçu, sans persistance).     |
| POST    | `/agriculture/parcel/neighbors` | Contexte des cultures déclarées dans un rayon donné autour d'un point.        |
| POST    | `/agriculture/analyze`          | Pipeline complet : sol/météo/satellite/DL + scoring + rapport IA + persistance.|
| GET     | `/health`                       | Health check.                                                                  |

## Lancer le serveur (dev local)

```bash
cd backend/agent_agriculture
python -m venv .venv
# macOS/Linux : source .venv/bin/activate — Windows : .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

Sur Linux/macOS/Docker, `pip install -r requirements.txt` installe tout d'un
coup sans souci. **Sur Windows**, `chromadb==0.5.15` pointe vers
`chroma-hnswlib==0.7.6`, qui n'a pas de wheel précompilé pour Windows/Python
3.12 (seulement les sources, qui nécessitent MSVC Build Tools pour compiler).
Si `pip install -r requirements.txt` échoue sur `chroma-hnswlib` avec
`Microsoft Visual C++ 14.0 or greater is required`, installez plutôt dans cet
ordre (dans le même venv) :

```powershell
pip install chroma-hnswlib==0.7.5   # a un wheel cp312-win_amd64 ; compatible en API avec 0.7.6
pip install chromadb==0.5.15 --no-deps
# installe le reste de requirements.txt SANS re-déclencher la résolution de
# dépendances de chromadb (qui retenterait 0.7.6). Filtrer aussi les commentaires
# et lignes vides — sinon pip reçoit des lignes `# ...` (ex. `numpy<2`) comme
# exigences invalides :
$pkgs = Get-Content requirements.txt | Where-Object {
  $_ -match '\S' -and $_ -notmatch '^\s*#' -and $_ -notmatch '^chromadb=='
}
pip install @pkgs
```

`pip` affichera un avertissement `chromadb ... requires chroma-hnswlib==0.7.6,
but you have chroma-hnswlib 0.7.5` à la fin — sans conséquence (patch version,
API identique), tout le reste s'installe et l'app démarre normalement.

Port `8002` par convention (`8000` = agent_business, `8001` = auth — voir leurs
README) afin de pouvoir lancer plusieurs agents en local simultanément sans
collision. Le frontend le cible via `VITE_AGENT_AGRICULTURE_URL` (défaut
`http://localhost:8002`, voir `frontend/.env.example`).

Variables d'environnement utilisées (toutes dans le `.env` racine du repo —
voir `.env.example`) :

- `DATABASE_URL` — Postgres/PostGIS, requis pour persister `land_profiles` /
  `crop_recommendations` (facultatif si vous n'utilisez que le point cliqué
  sur la carte, sans `terrain_id`).
- `MISTRAL_API_KEY` — requis pour le rapport IA (RAG + synthèse). Sans clé,
  `/agriculture/analyze` fonctionne quand même (sol/météo/satellite/scoring
  réels) mais `report` revient à `null` avec un avertissement dans
  `warnings`.
- `SENTINEL_HUB_CLIENT_ID` / `SENTINEL_HUB_CLIENT_SECRET` — compte gratuit sur
  [dataspace.copernicus.eu](https://dataspace.copernicus.eu), requis pour le
  NDVI et le classifieur DL. Sans ces clés, `vegetation`/`dl_observation`
  reviennent en `source: "unavailable"`.

Toutes les autres sources (cadastre IGN, RPG WFS, SoilGrids, Open-Meteo, HAL)
sont publiques, gratuites, sans clé.

## Alimenter le corpus RAG

```bash
cd backend/agent_agriculture
python -m scripts.fetch_hal_documents --query "ble tendre fertilisation" --coll INRAE --rows 30 --out ./corpus
python -m scripts.ingest_rag_corpus --input ./corpus --crop ble_tendre --topic fertilisation
python -m scripts.dedupe_chroma --apply   # nettoyage ponctuel des doublons
```

`chroma_store/` (persistance du vector store) est monté en volume Docker
(voir `docker-compose.yml`) pour survivre aux redémarrages du conteneur.

**Sur Windows**, `python -m scripts.ingest_rag_corpus` doit être lancé avec le
`python` du venv (`.venv\Scripts\python.exe`, pas le `python` global) puisque
`unstructured[pdf]` (et sa dépendance `pdfminer.six==20240706`, voir
`requirements.txt`) ne sont installés que dans le venv du projet. Le script
contourne aussi lui-même deux pièges Windows :

- **Pas de `libmagic`** (bibliothèque C absente par défaut sur Windows) :
  `unstructured` retombe dessus (via `python-magic`) pour la détection MIME
  quand aucun `content_type` n'est fourni, ce qui plantait avec
  `ImportError: failed to find libmagic`. Le script passe désormais un
  `content_type` explicite (déduit de l'extension) pour éviter ce chemin.
- **Console cp1252** : les anciens messages avec emojis (`⚠️`, `❌`, `⏭️`)
  provoquaient un `UnicodeEncodeError` à l'impression sur un terminal Windows
  par défaut, masquant l'erreur réelle. Remplacés par des tags ASCII
  (`[ATTENTION]`, `[ERREUR]`, `[SKIP]`).

Le parsing PDF via `pdfminer` reste lent pour des thèses/articles longs
(plusieurs minutes pour 20-30 PDFs) — c'est normal, le script continue en
arrière-plan fichier par fichier sans planter sur un document problématique.

## Classifieur DL (optionnel, Phase B)

Observation satellite indépendante du scoring (jamais utilisée pour classer
les cultures recommandées — voir `app/services/dl_service.py`) :

```bash
pip install breizhcrops
python -m scripts.finetune_dl_service --datapath ./breizhcrops_dataset --epochs 8 --out ./dl_checkpoints/tempcnn_finetuned.pth
```

Sans checkpoint présent à `DL_CHECKPOINT_PATH`, `dl_observation` revient en
`source: "unavailable"` — dégradation propre, pas une erreur bloquante.

## Tests

```bash
cd backend/agent_agriculture
python -m app.tests.test_endpoints   # rapide, sans réseau (scoring/agro-calc + /health)
```

Les intégrations réseau (cadastre/RPG/SoilGrids/Open-Meteo/Sentinel
Hub/Mistral) se testent manuellement contre un serveur lancé en local — voir
les routes ci-dessus avec un point réel (ex. `48.8566, 2.3522` couvre Paris
intra-muros, plutôt urbain ; préférer un point en zone rurale connue pour
tester un vrai retour RPG).

## Limitations connues (héritées du prototype d'origine)

- **Scoring des cultures** : règles/pondérations documentées dans
  `app/services/ml_service.py`, pas un modèle entraîné sur données RPG
  réelles — à remplacer par un vrai `RandomForestClassifier` une fois un
  jeu de données labellisé disponible (même shape de sortie, zéro
  changement ailleurs dans le pipeline).
- **Engrais/irrigation** : approximations COMIFER/FAO-56 documentées dans
  `app/services/agro_calc_service.py` (pas un vrai test de sol Nmin, pas un
  bilan hydrique de saison complète).
- **Besoins pesticides** : non calculés (nécessite un module BSV — voir
  ci-dessous).
- **Élévation** (`land_profiles.elevation_m`, Open-Elevation) : jamais
  implémentée dans le prototype d'origine — colonne laissée à `null`.
- **`/agriculture/ndvi_heatmap`** (grille de pixels NDVI, pas seulement la
  moyenne) : jamais implémenté dans le prototype d'origine non plus.

## À ajouter par rapport à l'existant

- Module BSV (Bulletin de Santé du Végétal) : croiser les données
  climatiques régionales avec les risques phytosanitaires connus (scarabée
  japonais, charançon rouge...) pour calculer `besoins_pesticides` — anticiper
  le problème n°2 dès cette étape.
- Un vrai agent (boucle de sélection d'outils) plutôt que le pipeline
  fixe actuel dans `app/routers/agriculture.py` — même contrats de données,
  routage à remplacer sans toucher aux services.
