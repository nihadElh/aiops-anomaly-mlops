# Risques, limites, éthique et gouvernance

| Risque | Conséquence | Mesure | Statut |
|--------|-------------|--------|--------|
| Fuite de données (choix du seuil ou du modèle sur le test, split non chronologique) | Performances surestimées | Seuil choisi sur validation, test utilisé une fois, split par ordre des lignes, test de non-chevauchement | À documenter |
| Hypothèse « ordre des lignes = temps » fausse | Split non réellement temporel | Vérifier avec l'ordre des logs d'origine ou les horodatages, signaler la limite | À vérifier |
| Déséquilibre de classes | Accuracy trompeuse, anomalies manquées | PR-AUC, rappel, class weights | Traité |
| Faux négatifs (incident manqué) | Panne non anticipée | Seuil orienté rappel, supervision humaine, alerte complémentaire | À analyser |
| Faux positifs | Fatigue des opérateurs, alertes ignorées | Précision minimale dans le gate, regroupement des alertes | À analyser |
| Généralisation | Un seul système (HDFS), logs anciens : mauvais transfert à d'autres infrastructures | Le dire explicitement, pas de généralisation | À écrire |
| Dérive des logs (mise à jour logicielle, nouveaux événements) | Dégradation silencieuse | PSI entrées/scores, taux d'événements inconnus, ré-entraînement planifié | Traité (monitoring) |
| Données personnelles dans les logs réels | Exposition | Logs d'API sans entrées brutes ; en production, masquage avant journalisation | À écrire |
| Mauvaise interprétation du score | Décision automatique injustifiée | Score = aide à la décision, jamais action automatique sans validation humaine | À écrire |
| Dépendances vulnérables | Faille de sécurité | `pip-audit` en CI | Traité |
| Licence des données | Usage non conforme | Citer la source et les conditions d'usage | À vérifier |

## Gouvernance
- Qui peut promouvoir un modèle en « Production » dans le Model Registry : décision documentée après passage du gate.
- Procédure de retour arrière : conserver la version précédente du modèle et la configuration associée.
- Revue périodique : seuils, dérive, taux d'alertes réelles confirmées.
