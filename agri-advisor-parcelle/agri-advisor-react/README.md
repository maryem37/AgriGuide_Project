# Agri Advisor IA — Frontend React

Interface React/TypeScript (Vite) pour le backend FastAPI "AI Agricultural
Advisor". Remplace `static/index.html` par une véritable SPA : carte
Leaflet interactive, résolution de parcelle, contexte des voisins RPG,
carte NDVI optionnelle, et rapport agronomique complet rendu dans un modal.

## ⚠️ Étape obligatoire côté backend : activer le CORS

Le frontend Vite tourne sur `http://localhost:5173`, le backend FastAPI sur
`http://127.0.0.1:8000` — **deux origines différentes**. Sans CORS activé,
le navigateur bloquera silencieusement tous les appels API (`/parcel/resolve`,
`/advise`, etc.), erreurs visibles uniquement dans la console du navigateur.

Ajoutez ceci dans `main.py`, juste après `app = FastAPI(...)` :

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Sans ce bloc, **rien ne fonctionnera**, même si tout le reste est correct.

## Installation

```bash
npm install
cp .env.example .env
```

`.env` pointe par défaut vers `http://127.0.0.1:8000` — ajustez si votre
backend tourne ailleurs.

## Lancer en développement

Terminal 1 (backend, depuis la racine du projet Python) :
```bash
uvicorn main:app --reload
```

Terminal 2 (frontend, depuis ce dossier) :
```bash
npm run dev
```

Ouvrez `http://localhost:5173`.

## Build de production

```bash
npm run build
npm run preview   # pour tester le build localement
```

Le dossier `dist/` peut être servi par n'importe quel serveur statique — ou,
si vous préférez tout servir depuis FastAPI comme avant, copiez le contenu
de `dist/` dans le dossier `static/` du backend et pointez `VITE_API_BASE_URL`
vers une URL relative (`""`) puisque tout serait alors sur la même origine
(le CORS ci-dessus ne serait alors même plus nécessaire).

## Structure

```
src/
  api/client.ts              Client fetch typé — un point d'entrée par route backend
  types/api.ts               Types miroir exact de schemas.py
  hooks/
    useParcelSelection.ts    État: point cliqué → résolution parcelle → voisins
    useAdvise.ts             État: appel /advise → rapport / erreur / chargement
  components/
    MapView.tsx              Carte Leaflet (react-leaflet) : clic, parcelle, voisins, NDVI
    Header.tsx
    Sidebar/                 Panneau latéral (statut, infos parcelle, voisins, boutons)
    Report/
      reportParser.ts        Parsing du markdown du rapport en sections typées
      ReportSections.tsx     Un renderer dédié par type de section (sol, météo, cultures...)
      ReportModal.tsx         Modal plein écran affiché après /advise
      Prose.tsx               Rendu markdown-lite (**gras**, *italique*) en JSX réel
```

## Notes

- **`/parcel/ndvi_heatmap`** : le bouton NDVI appelle cette route. Si elle
  n'existe pas encore côté backend (elle n'apparaissait pas dans les fichiers
  `services/`/`main.py` analysés), le bouton échoue proprement (message en
  console, pas de crash) — à implémenter côté FastAPI si vous voulez
  l'activer.
- Le rapport est rendu **dans l'app** (modal), pas dans un nouvel onglet
  `window.open` comme la version HTML précédente — meilleure intégration
  React, pas de blocage popup à gérer.
- Aucune donnée agronomique n'est codée en dur côté frontend : tout vient du
  backend, dans l'esprit du projet (`README.md` racine, §1).
