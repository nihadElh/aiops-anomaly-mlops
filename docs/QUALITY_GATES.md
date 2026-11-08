# Quality gates

Principe : un seuil n'est jamais arbitraire. Chaque ligne « Seuil » doit être justifiée par une baseline,
une exigence métier ou un compromis documenté. Les valeurs de `params.yaml > quality_gate` sont des
**valeurs de départ à remplacer** après les premières expériences.

| Niveau | Contrôle | Où | Résultat attendu | Seuil / origine |
|--------|----------|----|------------------|-----------------|
| Code | Lint `ruff`, tests `pytest` | CI | Échec du pipeline si un test échoue | — |
| Données | Schéma, doublons, labels, négatifs, NaN, anomalies présentes dans chaque split | `validate.py`, `data.py`, tests | Rejet des données invalides | — |
| Données | Provenance et version | hash SHA-256 dans `manifest.json`, tag MLflow | Traçabilité du jeu utilisé | — |
| Modèle | PR-AUC candidat ≥ PR-AUC baseline + marge | `gate.py` | Rejet si le candidat ne bat pas la baseline | **Marge : à fixer** à partir de l'écart-type observé sur plusieurs seeds |
| Modèle | Rappel minimal | `gate.py` | Rejet si trop d'incidents manqués | **À fixer** : exigence métier (coût d'un incident manqué) |
| Modèle | Précision minimale | `gate.py` | Rejet si trop de fausses alertes | **À fixer** : fatigue des opérateurs, capacité de traitement des alertes |
| Sécurité | `pip-audit`, absence de secrets | CI | Aucune vulnérabilité critique non traitée | Rendre l'étape bloquante quand tout est traité |
| Déploiement | `/health`, test d'intégration API | `tests/test_api.py` | Version démarrable et vérifiée | — |

## Limites de mesure à écrire dans le rapport
- Le gate est évalué sur un seul split temporel : il n'est pas un intervalle de confiance.
- Les métriques hors ligne ne garantissent pas la qualité observée après déploiement (dérive, nouveaux types de logs).
- Les données synthétiques de la CI valident la **mécanique** du pipeline, pas la qualité du modèle.
