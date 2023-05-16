# BioThings_TTD_Dataplugin Parser
Data source: https://db.idrblab.net/ttd/full-data-download
Version 8.1.01 (2021.11.08)

05/15/23

Matadata files: 5 files

From P1-01-TTD_target_download.txt:
- 4221 TARGETID (TARGETID	TTD Target ID)
- 3597 UNIPROID (Uniprot ID)
- 4080 TARGTYPE (Target Type)
- 2626 BIOCLASS (BioChemical Class)


From P1-05-Drug_disease.txt:
- 28978 INDICATI (Indication	Disease entry	ICD-11	Clinical status)
- 22597 TTDDRUID (TTD Drug ID)
- 22597 DRUGNAME (Drug Name)


From P1-06-Target_disease.txt:
- 2373 TARGETID (TTD Target ID)
- 2373 TARGNAME (Target Name)
- 10428 INDICATI (Clinical Status	Disease Entry [ICD-11])

From P1-07-Drug-TargetMapping.xlsx:

44663 entities
- TargetID
- DrugID
- Highest_status
- MOA (mode of activity)

From P1-08-Biomarker_disease.txt:

2512 "^BM.*$"
- BiomarkerID
- Biomarker_Name
- Diseasename
- ICD11
- ICD10
- ICD9
