# Audit HDFS_v1 — rapport de données

Généré le : 2026-11-08T19:50:24+00:00

Dossier source : `D:\projects\aiops-anomaly-mlops\data\raw\preprocessed`

**Confidentialité :** statistiques agrégées uniquement, aucun log brut ni identifiant de bloc exporté.

## Fichiers détectés

| Catégorie | Fichier | Taille (Mo) | Lignes |
|---|---|---:|---:|
| labels | anomaly_label.csv | 17.77 | 575061 |
| matrix | Event_occurrence_matrix.csv | 50.64 | 575061 |
| traces | Event_traces.csv | 119.6 | 575061 |
| templates | HDFS.log_templates.csv | 0.0 | 29 |

## Alertes et vérifications

- Risque de fuite de cible : Type (Success/Fail) dans la matrice. À EXCLURE des features.
- Risque de fuite de cible : Label de la matrice. À EXCLURE des features.

## labels

**Colonnes :** BlockId, Label

**Valeurs manquantes :** `{"BlockId": 0, "Label": 0}`

**duplicate_blockids :** `0`

**unique_blockids :** `575061`

**blank_blockids :** `0`

**label_counts :** `{"Normal": 558223, "Anomaly": 16838}`

**conflicting_duplicate_labels :** `0`

**anomaly_rate_pct :** `2.928`


## matrix

**Colonnes :** BlockId, Label, Type, E1, E2, E3, E4, E5, E6, E7, E8, E9, E10, E11, E12, E13, E14, E15, E16, E17, E18, E19, E20, E21, E22, E23, E24, E25, E26, E27, E28, E29

**Valeurs manquantes :** `{"BlockId": 0, "Label": 0, "Type": 558223, "E1": 0, "E2": 0, "E3": 0, "E4": 0, "E5": 0, "E6": 0, "E7": 0, "E8": 0, "E9": 0, "E10": 0, "E11": 0, "E12": 0, "E13": 0, "E14": 0, "E15": 0, "E16": 0, "E17": 0, "E18": 0, "E19": 0, "E20": 0, "E21": 0, "E22": 0, "E23": 0, "E24": 0, "E25": 0, "E26": 0, "E27": 0, "E28": 0, "E29": 0}`

**duplicate_blockids :** `0`

**unique_blockids :** `575061`

**blank_blockids :** `0`

**event_column_count :** `29`

**event_columns_preview :** `["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10", "E11", "E12"]`

**type_counts :** `{"<BLANK>": 558223, "21": 724, "31": 3225, "3": 2950, "4": 1240, "0": 2809, "7": 476, "1": 953, "16": 22, "9": 34, "5": 4167, "20": 7, "12": 130, "25": 2, "22": 9, "8": 45, "13": 10, "27": 3, "19": 8, "18": 9, "24": 3, "11": 3, "17": 3, "28": 1, "23": 1, "30": 1, "10": 3}`

**matrix_label_top_values :** `{"Success": 558223, "Fail": 16838}`

**groundtruth_join_counts :** `{"Normal": 558223, "Anomaly": 16838}`

**join_issues :** `{}`

**type_by_groundtruth :** `[{"Type": "<BLANK>", "GroundTruth": "Normal", "count": 558223}, {"Type": "21", "GroundTruth": "Anomaly", "count": 724}, {"Type": "4", "GroundTruth": "Anomaly", "count": 1240}, {"Type": "16", "GroundTruth": "Anomaly", "count": 22}, {"Type": "3", "GroundTruth": "Anomaly", "count": 2950}, {"Type": "31", "GroundTruth": "Anomaly", "count": 3225}, {"Type": "0", "GroundTruth": "Anomaly", "count": 2809}, {"Type": "7", "GroundTruth": "Anomaly", "count": 476}, {"Type": "1", "GroundTruth": "Anomaly", "count": 953}, {"Type": "9", "GroundTruth": "Anomaly", "count": 34}, {"Type": "5", "GroundTruth": "Anomaly", "count": 4167}, {"Type": "20", "GroundTruth": "Anomaly", "count": 7}, {"Type": "12", "GroundTruth": "Anomaly", "count": 130}, {"Type": "25", "GroundTruth": "Anomaly", "count": 2}, {"Type": "22", "GroundTruth": "Anomaly", "count": 9}, {"Type": "8", "GroundTruth": "Anomaly", "count": 45}, {"Type": "13", "GroundTruth": "Anomaly", "count": 10}, {"Type": "27", "GroundTruth": "Anomaly", "count": 3}, {"Type": "19", "GroundTruth": "Anomaly", "count": 8}, {"Type": "18", "GroundTruth": "Anomaly", "count": 9}, {"Type": "24", "GroundTruth": "Anomaly", "count": 3}, {"Type": "11", "GroundTruth": "Anomaly", "count": 3}, {"Type": "17", "GroundTruth": "Anomaly", "count": 3}, {"Type": "28", "GroundTruth": "Anomaly", "count": 1}, {"Type": "23", "GroundTruth": "Anomaly", "count": 1}, {"Type": "30", "GroundTruth": "Anomaly", "count": 1}, {"Type": "10", "GroundTruth": "Anomaly", "count": 3}]`

**matrix_label_presence_by_groundtruth :** `[{"MatrixLabel": "nonempty", "GroundTruth": "Normal", "count": 558223}, {"MatrixLabel": "nonempty", "GroundTruth": "Anomaly", "count": 16838}]`

**event_numeric_invalid_total :** `0`

**event_numeric_invalid_by_column :** `{"E1": 0, "E2": 0, "E3": 0, "E4": 0, "E5": 0, "E6": 0, "E7": 0, "E8": 0, "E9": 0, "E10": 0, "E11": 0, "E12": 0, "E13": 0, "E14": 0, "E15": 0, "E16": 0, "E17": 0, "E18": 0, "E19": 0, "E20": 0, "E21": 0, "E22": 0, "E23": 0, "E24": 0, "E25": 0, "E26": 0, "E27": 0, "E28": 0, "E29": 0}`

**event_negative_total :** `0`

**zero_event_rows :** `0`

**mean_events_per_block :** `19.434`

**max_events_per_block :** `298.0`

**top_events_by_total_occurrence :** `[["E5", 1723232.0], ["E26", 1719741.0], ["E11", 1706679.0], ["E9", 1706514.0], ["E21", 1402047.0], ["E23", 1396174.0], ["E22", 575061.0], ["E3", 428726.0], ["E4", 356207.0], ["E2", 120036.0], ["E6", 7097.0], ["E18", 7002.0], ["E25", 7002.0], ["E16", 6937.0], ["E20", 5545.0]]`

**top_events_by_blocks_present :** `[["E5", 575061], ["E22", 575061], ["E11", 568880], ["E9", 568854], ["E26", 568854], ["E21", 466647], ["E23", 465015], ["E3", 137434], ["E4", 129295], ["E2", 82705], ["E20", 5345], ["E18", 5271], ["E25", 5271], ["E6", 5243], ["E16", 5243]]`

**groundtruth_blockids_missing_in_matrix :** `0`

**event_columns_without_template :** `[]`


## traces

**Colonnes :** BlockId, Label, Type, Features, TimeInterval, Latency

**Valeurs manquantes :** `{"BlockId": 0, "Label": 0, "Type": 558223, "Features": 0, "TimeInterval": 0, "Latency": 0}`

**duplicate_blockids :** `0`

**unique_blockids :** `575061`

**blank_blockids :** `0`

**missing_in_groundtruth :** `0`

**missing_in_matrix :** `0`

**parsed_traces :** `575061`

**unparseable_or_empty_traces :** `0`

**trace_length_distribution :** `{"min": 2, "max": 298, "mean": 19.434, "most_common_lengths": [[19, 300482], [13, 96327], [25, 29894], [22, 26668], [20, 25071], [23, 21365], [28, 13220], [31, 13066], [24, 11781], [26, 7124], [14, 5582], [21, 4417], [4, 3225], [2, 2950], [27, 2690]]}`

**top_events_in_traces :** `[["E5", 1723232], ["E26", 1719741], ["E11", 1706679], ["E9", 1706514], ["E21", 1402047], ["E23", 1396174], ["E22", 575061], ["E3", 428726], ["E4", 356207], ["E2", 120036], ["E6", 7097], ["E18", 7002], ["E25", 7002], ["E16", 6937], ["E20", 5545]]`

**type_counts :** `{"<BLANK>": 558223, "21": 724, "4": 1240, "16": 22, "3": 2950, "31": 3225, "0": 2809, "7": 476, "1": 953, "9": 34, "5": 4167, "20": 7, "12": 130, "25": 2, "22": 9, "8": 45, "13": 10, "27": 3, "19": 8, "18": 9, "24": 3, "11": 3, "17": 3, "28": 1, "23": 1, "30": 1, "10": 3}`

**trace_label_presence :** `{"nonempty": 575061}`

**TimeInterval_presence :** `{"nonempty": 575061}`

**Latency_presence :** `{"nonempty": 575061}`

**groundtruth_blockids_missing_in_traces :** `0`


## templates

**Colonnes :** EventId, EventTemplate

**Valeurs manquantes :** `{"EventId": 0, "EventTemplate": 0}`

**duplicate_blockids :** `0`

**unique_blockids :** `0`

**blank_blockids :** `0`

**unique_eventids :** `29`

**duplicate_eventids :** `0`

**event_ids_preview :** `["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10", "E11", "E12"]`

## Prochaines décisions

1. Confirmer la colonne cible officielle via `anomaly_label.csv`.
2. Exclure `Type` et `Label` de la matrice des features avant tout entraînement.
3. Vérifier les correspondances de BlockId et la présence d’événements inconnus.
4. Définir une stratégie de split adaptée (pas de chronologie supposée).
5. Garder le test final isolé de la sélection des modèles.
