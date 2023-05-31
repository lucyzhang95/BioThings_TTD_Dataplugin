# BioThings_TTD_Dataplugin Parser
Data source: https://db.idrblab.net/ttd/full-data-download
Version 8.1.01 (2021.11.08)

P1-01-TTD_target_download.txt
| Entity | Count |
| --- | --- |
| TARGETID | 4221 |
| UNIPROID  | 3597 |
| TARGTYPE | 4080 |
| BIOCLASS | 2626 |

From P1-05-Drug_disease.txt:
| Entity | Count |
| --- | --- |
| TTDDRUID | 22597 |
| DRUGNAME  | 22597 |
| INDICATI | 28978 |
| Parser id | 28685 |

- Parser merged TTDDRUGID with the same INDICATI ICD11

From P1-06-Target_disease.txt:
| Entity | Count |
| --- | --- |
| TARGETID | 2373 |
| TARGNAME  | 2373 |
| INDICATI | 10428 |
| Parser id | 10411 |

- Parser merged TARGETID with the same INDICATI ICD11
- 17 duplicated TARGETID + INDICATI ICD11: 10428 - 10411 = 17

From P1-07-Drug-TargetMapping.xlsx:
| Entity | Count |
| --- | --- |
| All | 44663 |
| Parser id  | 44663 |

From P1-08-Biomarker_disease.txt:
| Entity | Count |
| --- | --- |
| All | 2512 |
| Parser id  | 2512 |

From P1-09-Target_compound_activity.txt:
| Entity | Count |
| --- | --- |
| All | 803580 |
| Parser id  | 803580 |
