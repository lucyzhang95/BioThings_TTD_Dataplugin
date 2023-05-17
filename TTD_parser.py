import os.path
import re
from collections import defaultdict

from biothings.utils.dataload import tabfile_feeder


def get_target_info(file_path):
    """get information from the P1-01-TTD_target_download.txt file
    information: target_id, uniprot, target_type, bioclass of drug

    Keyword arguments:
    file_path: directory stores P1-01-TTD_target_download.txt file
    """
    target_info_file = os.path.join(file_path, "P1-01-TTD_target_download.txt")
    assert os.path.exists(target_info_file)

    target_info = None

    for line in tabfile_feeder(target_info_file, header=40):
        if line != ["", "", "", "", ""]:
            if line[1].startswith("TARGETID"):
                target_info = {}
                target_info["target_id"] = line[2]
            elif "UNIPROID" in line[1]:
                target_info["uniprot"] = line[2]
            elif "TARGTYPE" in line[1]:
                target_info["target_type"] = line[2].lower()
            elif "BIOCLASS" in line[1]:
                target_info["bioclass"] = line[2]
        else:
            if target_info:
                yield target_info


def load_drug_target(file_path):
    """load data from P1-07-Drug-TargetMapping.xlsx file
        and clean up the data

    Keyword arguments:
    file_path: directory stores P1-07-Drug-TargetMapping.xlsx file
    """
    import pandas as pd

    drug_targ_file = os.path.join(file_path, "P1-07-Drug-TargetMapping.xlsx")
    assert os.path.exists(drug_targ_file)

    drug_target_data = pd.read_excel(drug_targ_file, engine="openpyxl").to_dict(orient="records")

    for dicts in drug_target_data:
        target_info = get_target_info(file_path)
        object_node = {"id": dicts["TargetID"], "type": "biolink:Protein"}
        drug_moa = dicts["MOA"]

        subject_node = {"id": dicts["DrugID"], "trial_status": dicts["Highest_status"].lower(), "type": "biolink:Drug"}
        if drug_moa != ".":
            subject_node["moa"] = drug_moa.lower()

        for d in target_info:
            if object_node["id"] == d["target_id"]:
                object_node.update(d)

        _id = f"{subject_node['id']}_associated_with_{object_node['id']}"
        association = {"predicate": "biolink:associated_with"}

        output_dict = {"_id": _id, "association": association, "object": object_node, "subject": subject_node}

        yield output_dict


def load_drug_dis_data(file_path):
    """load data from P1-05-Drug_disease.txt file
        and clean up the data

    Keyword arguments:
    file_path: directory stores 1-05-Drug_disease.txt file
    """
    drug_dis_file = os.path.join(file_path, "P1-05-Drug_disease.txt")
    assert os.path.exists(drug_dis_file)

    drug_dis_list = []

    drug_id = None
    drug_name = None

    for line in tabfile_feeder(drug_dis_file, header=22):
        if line != ["", "", "", "", ""]:
            if line[0] == "TTDDRUID":
                drug_id = line[1]
            elif line[0] == "DRUGNAME":
                drug_name = line[1]
            elif line[0] == "INDICATI":
                icd11 = line[1].split(":")[1].split("]")[0].strip()
                disease_name = line[1].split("[")[0].strip()
                trial_status = line[1].split("]")[1].strip().lower()

                if drug_id and drug_name:
                    _id = f"{drug_id}_{drug_name}_{icd11}"
                    dict1 = {"_id": _id, "status": trial_status, "disease": disease_name}
                    drug_dis_list.append(dict1)
                else:
                    print("Both TTDDRUID and DRUGNAME need to be provided.")

    merged_dicts = defaultdict(list)
    for d in drug_dis_list:
        merged_dicts[d["_id"]].append({"status": d["status"], "disease": d["disease"]})

    output_dict = {}

    for _id, trial_list in merged_dicts.items():
        drug_id = _id.split("_")[0]
        drug_name = _id.split("_")[1]
        icd11 = _id.split("_")[2]

        output_dict["_id"] = f"{drug_id}_treats_{icd11}"
        output_dict["association"] = {"predicate": "biolink:treats_", "clinical_trial": trial_list}
        output_dict["object"] = {"id": icd11, "icd11": icd11}
        output_dict["subject"] = {"id": drug_id, "name": drug_name, "type": "biolink:Drug"}
        disease = output_dict["association"]["clinical_trial"][0]["disease"]
        output_dict["object"]["name"] = disease
        output_dict["object"]["type"] = "biolink:Disease"

        yield output_dict


def load_target_dis_data(file_path):
    """load data from P1-06-Target_disease.txt file
        and clean up the data

    Keyword arguments:
    file_path: directory stores P1-06-Target_disease.txt file
    """
    target_dis_file = os.path.join(file_path, "P1-06-Target_disease.txt")
    assert os.path.exists(target_dis_file)

    subject_node = None

    for line in tabfile_feeder(target_dis_file, header=22):
        if line != [""]:
            if line[1] == "TARGETID":
                subject_node = {"id": line[2], "target_id": line[2], "name": None, "type": "biolink:Protein"}
            elif line[1] == "TARGNAME":
                subject_node["name"] = line[2]
            elif line[1] == "INDICATI":
                icd11 = line[3].split(":")[1].split("]")[0].strip()
                object_node = {
                    "id": icd11,
                    "icd11": icd11,
                    "name": line[3].split("[")[0].strip(),
                    "type": "biolink:Disease",
                }

                if subject_node and object_node:
                    _id = f"{subject_node['id']}_target_for_{object_node['icd11']}"
                    association = {"predicate": "biolink:target_for"}

                    target_info = get_target_info(file_path)
                    for d in target_info:
                        if d["target_id"] == subject_node["id"]:
                            subject_node.update(d)

                    output_dict = {
                        "_id": _id,
                        "association": association,
                        "object": object_node,
                        "subject": subject_node,
                    }

                    yield output_dict

                else:
                    print("Subject and object need to be provided.")


def cleanup_icds(line, icd_prefix):
    """clean up the icds data for loading biomarker_dis_data

    Keyword arguments:
    dict: dictionary in biomarker_dis_data
    icd_key: "ICD11", "ICD10", "ICD9"
    icd_prefix:  "ICD-11", "ICD-10", "ICD-9"
    """
    if line != "." and line.startswith(icd_prefix):
        icd = line.split(":")[1].strip()
        if icd.find(",") != -1:
            icd = [item.strip() for item in icd.split(",")]
            return icd
        else:
            return icd


def load_biomarker_dis_data(file_path):
    """load data from P1-08-Biomarker_disease.txt file

    Keyword arguments:
    file_path: directory stores P1-08-Biomarker_disease.txt file
    """
    biomarker_file = os.path.join(file_path, "P1-08-Biomarker_disease.txt")
    assert os.path.exists(biomarker_file)

    for line in tabfile_feeder(biomarker_file, header=16):
        if line:
            subject_node = {"id": line[3].split(":")[1].strip(), "name": line[2], "type": "biolink:Disease"}

            biomarker_name = line[1]

            icd_group = [(line[3], "ICD-11:"), (line[4], "ICD-10:"), (line[5], "ICD-9:")]

            for icd_line, icd_prefix in icd_group:
                icd_value = cleanup_icds(icd_line, icd_prefix)
                icd_key = icd_line.split(":")[0].replace("-", "").strip().lower()
                subject_node[icd_key] = icd_value

            new_subject_node = {k: v for k, v in subject_node.items() if v is not None}

            object_node = {"id": line[0], "type": "biolink:Biomarker"}

            disease_name = line[2].replace(" ", "_")

            pattern = re.match(r"(.*?)\((.+)\)\s*$", biomarker_name)

            if pattern:
                _id_biomarker = pattern.groups()[1]
                _id = f"{_id_biomarker}_biomarker_for_{disease_name}"
                object_node["name"] = pattern.groups()[0]
                object_node["symbol"] = _id_biomarker

            else:
                _id_biomarker = biomarker_name.replace(" ", "_")
                _id = f"{_id_biomarker}_biomarker_for_{disease_name}"
                object_node["name"] = _id_biomarker

            association = {"predicate": "biolink:biomarker_for"}

            output_dict = {"_id": _id, "association": association, "object": object_node, "subject": new_subject_node}

            yield output_dict


def load_drug_target_act(file_path):
    """load data from P1-09-Target_compound_activity.txt file

    Keyword arguments:
    file_path: directory stores P1-09-Target_compound_activity.txt file
    """
    activity_file = os.path.join(file_path, "P1-09-Target_compound_activity.txt")
    assert os.path.exists(activity_file)

    subject_node = {}
    object_node = {}

    for line in tabfile_feeder(activity_file, header=1):
        subject_node["id"] = line[2]
        subject_node["pubchem_cid"] = line[2]
        subject_node["TTD_id"] = line[1]
        subject_node["activity"] = line[3].replace(" ", "")
        subject_node["type"] = "biolink:Drug"

        object_node["id"] = line[0]
        object_node["type"] = "biolink:Protein"

        if subject_node and object_node:
            target_info = get_target_info(file_path)
            for d in target_info:
                if d["target_id"] == object_node["id"]:
                    object_node.update(d)

            _id = f"{subject_node['id']}_associated_with_{object_node['id']}"
            association = "biolink:associated_with"
            output_dict = {"_id": _id, "association": association, "object": object_node, "subject": subject_node}

            yield output_dict

        else:
            print("Subject and Object need to be provided.")


def load_data(file_path):
    """main data load function

    Keyword arguments:
    file_path: directory stores all downloaded data files
    """
    import itertools

    for doc in itertools.chain(
        load_drug_target(file_path),
        load_drug_dis_data(file_path),
        load_target_dis_data(file_path),
        load_biomarker_dis_data(file_path),
        load_drug_target_act(file_path),
    ):

        yield doc
