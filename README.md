# BioThings_TTD_Dataplugin Parser
Data source: https://db.idrblab.net/ttd/full-data-download
Version 8.1.01 (2021.11.08)

Last Updated: 07/26/23

***
# Summary

|Entity| Count |
|:--|:-----:|
|Total records| 876,192 |

- Final total records 876,192 (834,616 + 2,512 + 10,403 + 28,661 = 876,192)
- Input source file has 890,161 records
- The initial parser records were 889,851 (890,161 - 889,851 = 310 where 17 and 293 duplicates are removed from drug-disease and target-disease)
- 13,659 records are removed from the final parser output due to duplicated _id (mostly from records with the same CHEBI/PUBCHEM.COMPOUND and UniProtKB)

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
|28,661|chebi| 3842 |icd11|28,661|
||pubchem_compound| 7815 |mondo| 3844 |
||ttd_drug_id|28,661|||

  
<details><summary>click to expand for count of input data source</summary>

<br>

| Entity | Count | Notes |
| --- | --- | ---|
| TTDDRUID | 22,597 ||
| DRUGNAME  | 22,597 ||
| INDICATI | 28,978 | *input records |

- Parser merged TTDDRUGID with the same INDICATI ICD11
- 317 duplicated records are merged

</details>

<br>



## P1-06-Target_disease.txt
- parser function: load_drug_target(file_path)

|Target-Disease (target_for))| subject (Protein) | Number of records | object (Disease) | Number of records |
|:--------------------------:|:-----------------------:|:-----------------:|:----------------:|:-----------------:|
|10,403|ttd_target_id|10,403|icd11|10,403|
||uniprotkb|6,177|mondo|1,018|

<details><summary>click to expand for count of input data source</summary>
  
<br>

| Entity | Count | Notes
| --- | --- | --- |
| TARGETID | 2,373 ||
| TARGNAME  | 2,373 ||
| INDICATI | 10,428 | *input records |

- Parser merged TARGETID with the same INDICATI ICD11
- 17 duplicated TARGETID + INDICATI ICD11: 10428 - 10411 = 17
- Additional 8 duplicated records were removed after mapping icd11 to mondo and ttd_target_id to uniprotkb

</details>

<br>

## P1-07-Drug-TargetMapping.xlsx
- parser function: load_drug_target(file_path)

|Drug-Target (interacts_with)| subject (SmallMolecule) | Number of records | object (Protein) | Number of records |
|:--------------------------:|:-----------------------:|:-----------------:|:----------------:|:-----------------:|
|31,174|chebi|4,550|uniprotkb|19,836|
||pubchem_compound|15,865|ttd_target_id|31,174|
||ttd_drug_id|31,174|||

<details><summary>click to expand for count of input data source</summary>

<br>

| Entity | Count |
| --- | --- |
| DrugID | 44,663 |
| TargetID | 44,663 |
| MOA | 44,663 |
| Highest_status | 44,663 |

- 13,460 drug-target pairs overlapped with the P1-09 data, which were dealt together with the P1-09 parser
- The left 31,174 (44,663-13,460 = 31,203) were included in the output of this parser and 29 duplicated records were removed. (31,203-31,174 = 29)

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

## Merged P1-07 and P1-09:
|Drug-Target_Activity (interacts_with)| subject (SmallMolecule) | Number of records | object (Protein) | Number of records |
|:--------------------------:|:-----------------------:|:-----------------:|:----------------:|:-----------------:|
|834,616|pubchem_compound|819,307|uniprotkb|500,703|
||ttd_drug_id|834,616|ttd_target_id|834,616|

- 138 (803580+31174-834616 = 138) duplicated records were removed

