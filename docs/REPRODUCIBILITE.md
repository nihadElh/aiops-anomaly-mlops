# Dossier de reproductibilité

## Environnement (à compléter après la première exécution complète)
- OS : ...
- Python : ... (`python --version`)
- Dépendances : `pip freeze > requirements.lock` puis commit du fichier
- Seed : voir `params.yaml`

## Données
- Source et URL : ...
- Licence / conditions : ...
- Hash SHA-256 du fichier brut : copier la valeur de `data/processed/manifest.json`
- Version DVC : fichier `data/raw/Event_occurrence_matrix.csv.dvc`

## Reconstruction pas à pas
```bash
git clone <depot> && cd aiops-anomaly-mlops
python -m venv .venv && source .venv/bin/activate    # Windows : .venv\Scripts\activate
pip install -e ".[dev]"
# placer le fichier de données dans data/raw/ (ou dvc pull si un remote DVC est configuré)
dvc repro
python -m aiops.gate
python -m aiops.monitor
```

## Expériences
- Suivi : MLflow (`sqlite:///mlflow.db`), expérience `aiops-anomaly`
- Chaque run contient : paramètres, métriques de validation, commit Git, hash des données, modèle
- Modèle enregistré : `aiops-anomaly-detector` (Model Registry)

## Résultats attendus
Tableau à compléter avec les métriques de `artifacts/val_metrics.json` et `artifacts/test_metrics.json`.
