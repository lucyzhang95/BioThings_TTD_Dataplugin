# BioThings_TTD_Dataplugin Parser
Data source: https://db.idrblab.net/ttd/full-data-download
Version 8.1.01 (2021.11.08)

Last Updated: 07/10/23

***
# Summary

|Entity| Count |
|:--|:-----:|
|Total records| 876,675 |

- Input source file has 890,161 records
- Parser output has 887,888 records with duplicates.
- 11,213 records are removed due to duplicated _id (mostly from records with the same chebi/pubchem_cid and UniProtKB)

<details><summary>click to expand for biolink prefix and predicate</summary>
  
## X-BTE biolink id_prefixes:
- PUBCHEM.COMPOUND
- CHEBI
- TTD.DRUG (ttd_drug_id)
- UniProtKB
- TTD.TARGET (ttd_target_id)

## X-BTE biolink predicates:
- interacts_with
- treats
- target_for
- biomarker_for

</details> 

***

# Parser Output Counts

## P1-01-TTD_target_download.txt
<details><summary>click to expand for count of input data source</summary>
  
- Entity count from input data source file

| Entity | Count |             
| --- | --- |
| TARGETID | 4221 |
| UNIPROID  | 3597 |
| TARGTYPE | 4080 |
| BIOCLASS | 2626 |

- UniProtAC labels: 3597 (str + list of str), 3851 (str)
- Unique UniProtAC labels: 3448 (str)
</details>

<br>

## P1-05-Drug_disease.txt
- parser function: load_drug_dis_data(file_path)

|Drug-Disease (treats))| subject (SmallMolecule) | Number of records | object (Disease) | Number of records |
|:--------------------------:|:-----------------------:|:-----------------:|:----------------:|:-----------------:|
|28,667|chebi|3,824|icd11|28,667|
||pubchem_compound|11,663|mondo|3,847|
||ttd_drug_id|28,667|||

  
<details><summary>click to expand for count of input data source</summary>

<br>

| Entity | Count | Notes |
| --- | --- | ---|
| TTDDRUID | 22,597 ||
| DRUGNAME  | 22,597 ||
| INDICATI | 28,978 | *parser records |

- Parser merged TTDDRUGID with the same INDICATI ICD11
- 311 duplicated records are merged

</details>

<br>



## P1-06-Target_disease.txt
- parser function: load_drug_target(file_path)

|Target-Disease (target_for))| subject (Protein) | Number of records | object (Disease) | Number of records |
|:--------------------------:|:-----------------------:|:-----------------:|:----------------:|:-----------------:|
|10,411|ttd_target_id|10,411|icd11|10,411|
||uniprotkb|6,183|mondo|1,026|

<details><summary>click to expand for count of input data source</summary>
  
<br>

| Entity | Count | Notes
| --- | --- | --- |
| TARGETID | 2,373 ||
| TARGNAME  | 2,373 ||
| INDICATI | 10,428 |*parser records |

- Parser merged TARGETID with the same INDICATI ICD11
- 17 duplicated TARGETID + INDICATI ICD11: 10428 - 10411 = 17

</details>

<br>

## P1-07-Drug-TargetMapping.xlsx
- parser function: load_drug_target(file_path)

|Drug-Target (interacts_with)| subject (SmallMolecule) | Number of records | object (Protein) | Number of records |
|:--------------------------:|:-----------------------:|:-----------------:|:----------------:|:-----------------:|
|42,718|chebi|6892|uniprotkb|28,509|
||pubchem_compound|33,744|ttd_target_id|42,718|
||ttd_drug_id|42,718|||

<details><summary>click to expand for count of input data source</summary>

<br>

| Entity | Count |
| --- | --- |
| DrugID | 44,663 |
| TargetID | 44,663 |
| MOA | 44,663 |
| Highest_status | 44,663 |

- 1,945 duplicated drug-target pairs are removed (due to the same pubchem_compound or chebi with different ttd drug ids)

</details>

<br>

## P1-08-Biomarker_disease.txt
- parser function: load_biomarker_dis_data(file_path)

|Biomarker-Disease (biomarker_for | subject (Disease) | Number of records | object  (Biomarker) | Number of records |
|:--------------------------:|:-----------------------:|:-----------------:|:----------------:|:-----------------:|
|2,512|icd11|2,512|ttd_biomarker_id|2,512|
||mondo|1,112|||

<details><summary>click to expand for count of input data source</summary>

<br>

| Entity | Count |
| --- | --- |
| BiomarkerID | 2,512 |
| Biomarker_Name | 2,512 |
| Diseasename | 2,512 |
| ICD11 | 2,512 |
| ICD10 | |
| ICD9 | |


</details>

<br>

## P1-09-Target_compound_activity.txt
- parser function: load_drug_target_act(file_path)

|Drug-Target_Activity (interacts_with)| subject (SmallMolecule) | Number of records | object (Protein) | Number of records |
|:--------------------------:|:-----------------------:|:-----------------:|:----------------:|:-----------------:|
|803,580|pubchem_compound|803,580|uniprotkb|480,975|
||ttd_drug_id|803,580|ttd_target_id|803,580|

<details><summary>click to expand for count of input data source</summary>

<br>

| Entity | Count |
| --- | --- |
| TTD Target ID | 803,580 |
| TTD Drug/Compound ID | 803,580 |
| Pubchem CID | 803,580 |
| Activity | 803,580 |

</details>
