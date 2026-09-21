# Risk Analyst Agent (`agent_risk`) — Port 8010

Microservice FastAPI d'évaluation centralisée des risques agricoles pour AgriGuide :
1. **Risque Climatique & Sécheresse Paramétrique** (`POST /risk/climate`) : Modèle fondé sur des preuves scientifiques (Belhsen et al., 2026, JRACR, doi:10.54560/jracr.v16i2.726) combinant SPI (loi Gamma), SPEI (loi Pearson III) et décrément NDVI.
2. **Rapport HTML/PDF d'Aide à la Décision** (`POST /risk/climate/report`) : Document autonome en 8 sections avec graphiques vectoriels SVG natifs en ligne.
3. **Risque de Concentration Spatiale / Monoculture** (`POST /risk/crop-mix`) : Indice Herfindahl-Hirschman (HHI) et optimisation d'asassolement par programmation linéaire (`scipy.optimize.linprog`).

## Démarrage rapide

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```
