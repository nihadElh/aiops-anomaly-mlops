# Plan du rapport technique (8 à 12 pages)

| # | Section | Pages | Contenu attendu (cahier des charges) |
|---|---------|-------|--------------------------------------|
| 1 | Problème et cadrage | 1 | Pourquoi détecter ces anomalies, qui utilise le système, coût d'une fausse alerte vs d'un incident manqué, métrique principale (PR-AUC) et justification |
| 2 | Données | 1–1,5 | Source (Loghub-HDFS), licence, structure, volumétrie, taux d'anomalies, qualité, limites (labels, ancienneté, un seul système) |
| 3 | Architecture et pipeline | 1 | Schéma (README), choix techniques, versionnement DVC/Git/MLflow |
| 4 | Protocole d'évaluation | 1 | Split chronologique, hypothèse « ordre des lignes = temps », seuil choisi sur validation, test utilisé une seule fois, **risques de fuite** |
| 5 | Expériences et résultats | 2 | Baseline vs candidat (≥ 2 configurations), PR-AUC / précision / rappel / F1, matrice de confusion, analyse des erreurs (faux négatifs), variabilité entre seeds |
| 6 | Tests et quality gates | 1 | Tableau de `QUALITY_GATES.md`, origine de chaque seuil |
| 7 | Déploiement et monitoring | 1 | API, journaux, latence P95, erreurs, dérive PSI, scénario de dérive simulée |
| 8 | Risques, limites, éthique | 1 | `RISQUES_GOUVERNANCE.md` : métriques hors ligne vs qualité réelle, biais, conséquences d'une erreur |
| 9 | Conclusion | 0,5 | Ce qui fonctionne, ce qui ne fonctionne pas, pistes |

## Les 7 questions du cahier (section 11) à traiter avant de coder

1. **Problème précis** : détecter les blocs HDFS anormaux à partir de la séquence d'événements de leurs logs.
2. **Données et droits** : Loghub (usage de recherche) — vérifier et citer la licence.
3. **Résultat attendu et évaluation** : PR-AUC, précision/rappel au seuil choisi sur validation, test final unique.
4. **Versions à conserver** : données (hash DVC), `params.yaml`, code (commit Git), modèles (MLflow Registry).
5. **Tests anti-régression** : schéma, absence de fuite, gate PR-AUC vs baseline, tests d'API.
6. **Événements et indicateurs observés** : latence P95, taux d'erreur, taux d'alertes, PSI entrées/scores, événements inconnus.
7. **Risques principaux** : voir `RISQUES_GOUVERNANCE.md`.

## Analyses qui feront la différence
- Distribution des faux négatifs : quels types d'événements sont manqués ?
- Sensibilité du seuil : courbe précision/rappel et coût opérationnel des alertes.
- Stabilité : mêmes résultats sur 3 seeds ? (justifie la marge du gate)
- Dérive simulée : à partir de quel niveau de PSI la qualité se dégrade-t-elle réellement ?
