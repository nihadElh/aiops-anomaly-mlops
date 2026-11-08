# AIOps — Détection d'anomalies sur logs système (HDFS)

Projet MLOps (ENSAF / ISDIA3 — *MLOps : stratégies de déploiement et considérations éthiques*), sujet 4 :
industrialisation d'un pipeline d'apprentissage automatique classique.

**Problème** : à partir des événements de journaux d'un système distribué (HDFS), détecter les blocs
anormaux (précurseurs d'incidents) pour réduire le temps de détection côté exploitation IT/réseau.

> Statut : squelette fonctionnel testé sur données **synthétiques** (CI). Les résultats réels sont à produire
> sur Loghub-HDFS et à consigner dans `docs/` et le rapport. Ne jamais présenter les scores synthétiques comme réels.

## Architecture

```
Event_occurrence_matrix.csv (DVC)
  -> prepare : validation du schéma, label binaire, split chronologique 70/15/15, manifeste (hash)
  -> train   : régression logistique (baseline) + HistGradientBoosting, suivi MLflow, choix sur VALIDATION
  -> evaluate: métriques sur TEST (une seule fois), PR-AUC / précision / rappel / F1
  -> gate    : acceptation ou rejet automatique (CI)
  -> API FastAPI (/health, /predict, /metrics) + journaux JSON lines
  -> monitor : dérive (PSI) des entrées et des scores, latence P95, taux d'erreur
```

## Installation

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate      Linux/macOS : source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Données

Télécharger le jeu **Loghub / HDFS_v1 prétraité** (matrice d'occurrence des événements par bloc) depuis le dépôt
`logpai/loghub` ou sa page Zenodo, et le placer dans `data/raw/Event_occurrence_matrix.csv`.
**À vérifier avant de continuer** : noms de colonnes (`BlockId`, `Label`, `E1..E29`), valeurs de `Label`
(`Normal`/`Anomaly`), conditions d'utilisation. Adapter `params.yaml > data` si nécessaire.
Hypothèse à confirmer et documenter : l'ordre des lignes sert de proxy du temps pour le split chronologique.

## Exécution

```bash
dvc init                                   # une seule fois, puis commit du dossier .dvc
dvc add data/raw/Event_occurrence_matrix.csv
dvc repro                                  # prepare -> train -> evaluate
python -m aiops.gate                       # quality gate (code retour 1 si rejet)
python -m aiops.monitor                    # rapport de dérive -> artifacts/drift_report.json
uvicorn aiops.api:app --port 8000          # API ; docs interactives : http://localhost:8000/docs
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

Sans DVC, chaque étape se lance aussi à la main : `python -m aiops.data`, `python -m aiops.train`,
`python -m aiops.evaluate`.

Exemple d'appel : `curl -X POST localhost:8000/predict -H "Content-Type: application/json" -d '{"counts":[2,0,5,...]}'`
(29 valeurs : une par type d'événement).

## Tests et CI

```bash
ruff check src tests scripts
pytest -q
python scripts/run_sample_pipeline.py     # pipeline complet sur données synthétiques
```

La CI (`.github/workflows/ci.yml`) exécute lint, tests, pipeline synthétique et audit des dépendances.
Détail et justification des seuils : `docs/QUALITY_GATES.md`.

## Documentation

- `docs/PLAN_RAPPORT.md` — plan du rapport (8–12 pages) aligné sur le cahier des charges
- `docs/QUALITY_GATES.md` — contrôles automatiques et origine des seuils
- `docs/RISQUES_GOUVERNANCE.md` — risques, limites, éthique
- `docs/REPRODUCIBILITE.md` — versions, commandes, reconstruction

## Sécurité

Aucun secret dans le dépôt : `.env` est ignoré, `.env.example` ne contient aucune valeur sensible.
Les journaux de l'API n'enregistrent pas les entrées brutes.
