import os.path
import pandas as pd
import numpy as np
import sys
import json
import re


def get_target_info(file_path):
    target_info_file = os.path.join(file_path, "P1-01-TTD_target_download.txt")
    assert os.path.exists(target_info_file)

    target_info = {"target_id": None,
                   "uniproid": None,
                   "target_type": None,
                   "bioclass": None}

    with open(target_info_file) as target_info_file:
        for line in target_info_file:
            line = line.strip().split("\t")
            if line != ['']:
                if line[1] == "TARGETID":
                    target_id = line[2]
                    target_info["target_id"] = target_id
                elif line[1] == "UNIPROID":
                    uniproid = line[2]
                    target_info["uniproid"] = uniproid
                elif line[1] == "TARGTYPE":
                    target_type = line[2]
                    target_info["target_type"] = target_type
                elif line[1] == "BIOCLASS":
                    bioclass = line[2]
                    target_info["bioclass"] = bioclass

                yield target_info


def get_drug_MOA(file_path):
    file = os.path.join(file_path, "P1-07-Drug-TargetMapping.csv")
    drug_target_data = pd.read_csv(file).to_dict(orient="records")

    drug_id = [dicts["DrugID"] for dicts in drug_target_data]
    drug_moa = [dicts["MOA"] for dicts in drug_target_data]

    drug_moa_dict = {k: v for (k, v) in zip(drug_id, drug_moa)}

    yield drug_moa_dict


def load_drug_dis_data(file_path):
    drug_dis_file = os.path.join(file_path, "P1-05-Drug_disease.txt")
    assert os.path.exists(drug_dis_file)

    with open(drug_dis_file) as file:
        for line in file:
            line = line.strip().split("\t")

            if line[0] == "TTDDRUID":
                subject_node = {"id": line[1],
                                "name": None,
                                "trial_status": None}
            elif line[0] == "DRUGNAME":
                subject_node["name"] = line[1]
            elif line[0] == "INDICATI":
                subject_node["type"] = "Drug"
                subject_node["trial_status"] = line[1].split("]")[1].strip()

                object_node = {"icd11": line[1].split(":")[1].split("]")[0].strip(),
                               "name": line[1].split("[")[0].strip(),
                               "type": "Disease"}

                drug_moa_data = get_drug_MOA(file_path)
                ids = subject_node["id"]
                for items in drug_moa_data:
                    if subject_node["id"] in items:
                        subject_node["moa"] = items[ids]

                _id = f"{ids}_treats_{object_node['icd11']}"

                dat_dict = {
                    "_id": _id,
                    "object": object_node,
                    "subject": subject_node}

                yield dat_dict


def load_target_dis_data(file_path):
    target_dis_file = os.path.join(file_path, "P1-06-Target_disease.txt")
    assert os.path.exists

    with open(target_dis_file) as file:
        for line in file:
            line = line.strip().split("\t")

            if line != ['']:
                if line[1] == "TARGETID":
                    subject_node = {"id": line[2],
                                    "name": None,
                                    "type": "Protein"}
                elif line[1] == "TARGNAME":
                    subject_node["name"] = line[2]
                elif line[1] == "INDICATI":
                    object_node = {"icd11": line[3].split(":")[1].split("]")[0].strip(),
                                   "name": line[3].split("[")[0].strip(),
                                   "type": "Disease"}

                    association = {"predicate": line[2]}

                    target_info = get_target_info(file_path)
                    for d in target_info:
                        if d["target_id"] == subject_node["id"]:
                            subject_node["uniproid"] = d["uniproid"]
                            subject_node["target_type"] = d["target_type"]
                            subject_node["bioclass"] = d["bioclass"]

                    _id = f"{subject_node['id']}_target_for_{object_node['icd11']}"

                    dat_dict = {
                        "_id": _id,
                        "association": association,
                        "object": object_node,
                        "subject": subject_node}

                    yield dat_dict


def load_biomarker_dis_data(file_path):
    file_local = os.path.join(file_path, "P1-08-Biomarker_disease.txt")

    biomarker_list = pd.read_table(file_local, sep="\t").to_dict(orient='records')

    for dicts in biomarker_list:
        disease_name = dicts["Diseasename"].replace(" ", "_")
        subject_node = {"icd": [],
                        "name": disease_name,
                        "type": "Disease"}

        subject_node["icd"].extend([dicts["ICD11"], dicts["ICD10"], dicts["ICD9"]])

        if "." in subject_node["icd"]:
            subject_node["icd"].remove(".")

        biomarker_name = dicts["Biomarker_Name"].replace(" ", "_")
        object_node = {"id": dicts["BiomarkerID"],
                       "name": biomarker_name,
                       "type": "Biomarker"}

        if "(" in biomarker_name:
            _id = f"{biomarker_name.split('(')[1].split(')')[0]}_biomarker_for_{disease_name}"
        else:
            _id = f"{biomarker_name}_biomarker_for_{disease_name}"

        association = {"predicate": "biomarker"}

        dat_dict = {"_id": _id,
                    "association": association,
                    "object": object_node,
                    "subject": subject_node}

        yield dat_dict
