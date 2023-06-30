# BioThings_TTD_Dataplugin Parser
Data source: https://db.idrblab.net/ttd/full-data-download
Version 8.1.01 (2021.11.08)

06/29/23

# Summary
|Entity| Count |
|:--|:-----:|
|Total records| 882,636 |
|Unmapped TTD records | 62,411 |
|Object with id prefix| 880,124 |
|Subject with id prefix| 882,636 |

## X-BTE biolink id_prefixes:
- UniProtKB
- CHEBI
- PUBCHEM.COMPOUND
- ICD11


## P1-01-TTD_target_download.txt
| Entity | Count |             
| --- | --- |
| TARGETID | 4221 |
| UNIPROID  | 3597 |
| TARGTYPE | 4080 |
| BIOCLASS | 2626 |

- UniProtAC labels: 3597 (str + list of str), 3851 (str)
- Unique UniProtAC labels: 3448 (str)

## P1-05-Drug_disease.txt
| Entity | Count |
| --- | --- |
| TTDDRUID | 22,597 |
| DRUGNAME  | 22,597 |
| INDICATI | 28,978 |
| Parser id | 26,626 |

- Parser merged TTDDRUGID with the same INDICATI ICD11


## P1-06-Target_disease.txt
| Entity | Count |
| --- | --- |
| TARGETID | 2,373 |
| TARGNAME  | 2,373 |
| INDICATI | 10,428 |
| Parser id | 10,411 |

- Parser merged TARGETID with the same INDICATI ICD11
- 17 duplicated TARGETID + INDICATI ICD11: 10428 - 10411 = 17


## P1-07-Drug-TargetMapping.xlsx
| Entity | Count |
| --- | --- |
| All | 44,663 |
| Parser id  | 39,511 |

## P1-08-Biomarker_disease.txt
| Entity | Count |
| --- | --- |
| All | 2,512 |
| Parser id  | 2,512 |


## P1-09-Target_compound_activity.txt
| Entity | Count |
| --- | --- |
| All | 803,580 |
| Parser id  | 803,580 |
