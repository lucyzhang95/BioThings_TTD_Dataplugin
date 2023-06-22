import os.path
import re
import aiohttp
import aiohttp.client_exceptions
import asyncio
from collections import defaultdict

from biothings.utils.dataload import tabfile_feeder


class UniprotJobIDs:
    def __init__(self, file_path):
        self.file_path = file_path
        self.job_ids = []
        self.api_url = "https://rest.uniprot.org"

    def get_uniprot_ac(self):
        uniprot_info_file = os.path.join(self.file_path, "P1-01-TTD_target_download.txt")
        assert os.path.exists(uniprot_info_file)

        ac_dict = None
        for line in tabfile_feeder(uniprot_info_file, header=40):
            if line[1].startswith("TARGETID"):
                ac_dict = {"ttd_target_id": line[2]}
            elif "UNIPROID" in line[1]:
                delimiter_pattern = r'[;/-]'
                if ";" in line[2] or "/" in line[2] or "-" in line[2] and "(" not in line[2]:
                    uniprot_ac = re.split(delimiter_pattern, line[2])
                    uniprot_ac = [item.strip() for item in uniprot_ac]
                    ac_dict["uniprot_ac"] = uniprot_ac
                elif "(" in line[2]:
                    for ac in line[2].split("(")[0]:
                        uniprot_ac = ac.strip()
                        ac_dict["uniprot_ac"] = uniprot_ac
                else:
                    ac_dict["uniprot_ac"] = line[2]

                if ac_dict:
                    yield ac_dict

    def get_tasks(self, session):
        tasks = []
        ac_info = self.get_uniprot_ac()
        for ac_dict in ac_info:
            if not isinstance(ac_dict["uniprot_ac"], list):
                data = {"from": "UniProtKB_AC-ID", "to": "UniProtKB", "ids": ac_dict["uniprot_ac"]}
                tasks.append(asyncio.create_task(session.post(f"{self.api_url}/idmapping/run", data=data)))
            else:
                for ac in ac_dict["uniprot_ac"]:
                    data = {"from": "UniProtKB_AC-ID", "to": "UniProtKB", "ids": ac}
                    tasks.append(asyncio.create_task(session.post(f"{self.api_url}/idmapping/run", data=data)))
        return tasks

    async def get_jobIds(self):
        async with aiohttp.ClientSession() as session:
            tasks = self.get_tasks(session)
            responses = await asyncio.gather(*tasks)
            for response in responses:
                self.job_ids.append(await response.json())

    def run_async_task_job_ids(self):
        asyncio.run(self.get_jobIds())


class MappedUniprotKbs:
    def __init__(self, job_ids):
        self.job_ids = job_ids
        self.uniprot_ac_kb = []
        self.api_url = "https://rest.uniprot.org"

    def get_jobId_mapping_link(self, session):
        tasks = []
        for d in self.job_ids:
            for job_id in d.values():
                get_response = session.get(f"{self.api_url}/idmapping/uniprotkb/results/{job_id}", ssl=False)
                tasks.append(asyncio.create_task(get_response))
        return tasks

    async def get_mapped_uniprot_kbs(self):
        async with aiohttp.ClientSession(trust_env=True, timeout=aiohttp.ClientTimeout(total=300)) as session:
            tasks = self.get_jobId_mapping_link(session)
            batch_size = 10
            task_batches = [tasks[i:i + batch_size] for i in range(0, len(tasks), batch_size)]

            for batch in task_batches:
                batch_result = await asyncio.gather(*batch)
                for response in batch_result:
                    try:
                        results = await response.json()
                        if results["results"]:
                            if "failedIds" not in results:
                                ac = results["results"][0]["from"]
                                kb = results["results"][0]["to"]["primaryAccession"]
                                mapped_dict = {"uniprot_kb": kb, "uniprot_ac": ac}
                                self.uniprot_ac_kb.append(mapped_dict)
                            else:
                                pass
                    except (aiohttp.client_exceptions.ClientOSError,
                            aiohttp.client_exceptions.ServerDisconnectedError):
                        await asyncio.sleep(3)  # To avoid hammering the server


class UniprotMapping:
    def __init__(self, file_path):
        self.file_path = file_path

    def run_async_tasks(self):
        job_ids_obj = UniprotJobIDs(self.file_path)
        job_ids_obj.run_async_task_job_ids()

        mapped_uniprot_obj = MappedUniprotKbs(job_ids_obj.job_ids)
        asyncio.run(mapped_uniprot_obj.get_mapped_uniprot_kbs())

        mapped_uniprot_kbs = mapped_uniprot_obj.uniprot_ac_kb
        ac_info = UniprotJobIDs(self.file_path).get_uniprot_ac()
        ac_dict = {d["ttd_target_id"]: d["uniprot_ac"] for d in ac_info}
        final_list = []
        for d in mapped_uniprot_kbs:
            for key, value in ac_dict.items():
                if d["uniprot_ac"] in value:
                    d["ttd_target_id"] = key

        merged_uniprot_dict = defaultdict(list)
        for d in mapped_uniprot_kbs:
            merged_uniprot_dict[d.get("ttd_target_id")].append(d["uniprot_kb"])

        for key, value in merged_uniprot_dict.items():
            output_dict = {"ttd_target_id": key, "uniprot": value}
            output_dict["uniprot"] = list(set(output_dict["uniprot"]))
            final_list.append(output_dict)
        yield final_list


def get_target_info(file_path):
    """get information from the P1-01-TTD_target_download.txt file
    information: target_id, uniprot, target_type, bioclass of drug

    Keyword arguments:
    file_path: directory stores P1-01-TTD_target_download.txt file
    """
    target_info_file = os.path.join(file_path, "P1-01-TTD_target_download.txt")
    assert os.path.exists(target_info_file)

    target_info = None
    uniprot_class = UniprotMapping(file_path)
    uniprot_info = uniprot_class.run_async_tasks()
    for data in uniprot_info:
        uniprot_dict = {d["ttd_target_id"]: d for d in data}

        for line in tabfile_feeder(target_info_file, header=40):
            if line != ["", "", "", "", ""]:
                if line[1].startswith("TARGETID"):
                    if line[2] in uniprot_dict:
                        target_info = {"ttd_target_id": line[2],
                                       "uniprot": uniprot_dict[line[2]]["uniprot"]}
                    else:
                        target_info = {"ttd_target_id": line[2]}
                elif "TARGTYPE" in line[1]:
                    target_info["target_type"] = line[2].lower()
                elif "BIOCLASS" in line[1]:
                    target_info["bioclass"] = line[2]
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

    target_info_d = {d["ttd_target_id"]: d for d in get_target_info(file_path)}

    for dicts in drug_target_data:
        drug_moa = dicts["MOA"]

        subject_node = {
            "id": dicts["DrugID"],
            "type": "biolink:Drug",
        }

        if dicts["TargetID"] in target_info_d:
            if "uniprot" not in target_info_d[dicts["TargetID"]]:
                object_node = {"id": f"ttd_target_id:{dicts['TargetID']}"}
                object_node.update(target_info_d[dicts["TargetID"]])
            else:
                object_node = {"id": f"uniprot:{target_info_d[dicts['TargetID']].get('uniprot')[0]}",
                               "type": "biolink:Protein"}
                object_node.update(target_info_d[dicts["TargetID"]])

                _id = f"{subject_node['id']}_associated_with_{object_node['id'].split(':')[1]}"
                association = {"predicate": "biolink:associated_with", "trial_status": dicts["Highest_status"].lower()}
                if drug_moa != ".":
                    association["moa"] = drug_moa.lower()

                output_dict = {
                    "_id": _id,
                    "association": association,
                    "object": object_node,
                    "subject": subject_node,
                }

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
        # data file has empty spaces
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
                    dict1 = {
                        "_id": _id,
                        "status": trial_status,
                        "disease": disease_name,
                    }
                    drug_dis_list.append(dict1)
                else:
                    print("Both TTDDRUID and DRUGNAME need to be provided.")

    merged_dicts = defaultdict(list)

    # Merge the dict1 status and disease values with the same _id key
    for d in drug_dis_list:
        merged_dicts[d["_id"]].append({"status": d["status"], "disease": d["disease"]})

    for _id, trial_list in merged_dicts.items():
        drug_id = _id.split("_")[0]
        drug_name = _id.split("_")[1]
        icd11 = _id.split("_")[2]

        association = {"predicate": "biolink:treats", "clinical_trial": trial_list}

        object_node = {
            "id": icd11,
            "icd11": icd11,
            "name": association["clinical_trial"][0]["disease"],
            "type": "biolink:Disease",
        }

        subject_node = {"id": drug_id, "name": drug_name, "type": "biolink:Drug"}

        output_dict = {
            "_id": f"{drug_id}_treats_{icd11}",
            "association": association,
            "object": object_node,
            "subject": subject_node,
        }
        yield output_dict


def load_target_dis_data(file_path):
    """load data from P1-06-Target_disease.txt file
        and clean up the data

    Keyword arguments:
    file_path: directory stores P1-06-Target_disease.txt file
    """
    target_dis_file = os.path.join(file_path, "P1-06-Target_disease.txt")
    assert os.path.exists(target_dis_file)

    target_info_d = {d["target_id"]: d for d in get_target_info(file_path)}

    targ_dis_list = []

    targ_id = None
    targ_name = None

    for line in tabfile_feeder(target_dis_file, header=22):
        if line != [""]:
            if line[1] == "TARGETID":
                targ_id = line[2]
            elif line[1] == "TARGNAME":
                targ_name = line[2]
            elif line[1] == "INDICATI":
                icd11 = line[3].split(":")[1].split("]")[0].strip()
                disease_name = line[3].split("[")[0].strip()

                if targ_id and targ_name:
                    dict1 = {
                        "_id": f"{targ_id}_{targ_name}_{icd11}",
                        "status": line[2].split("\t")[0],
                        "disease": disease_name,
                    }
                    targ_dis_list.append(dict1)
                else:
                    print("Both target id and target name need to be provided.")

    merged_dict = defaultdict(list)
    for d in targ_dis_list:
        merged_dict[d["_id"]].append({"status": d["status"], "disease": d["disease"]})

    for _id, trial_list in merged_dict.items():
        targ_id = _id.split("_")[0]
        targ_name = _id.split("_")[1]
        icd11 = _id.split("_")[2]

        association = {
            "predicate": "biolink:target_for",
            "clinical_trial": trial_list,
        }
        _id = f"{targ_id}_target_for_{icd11}"

        subject_node = {
            "id": targ_id,
            "name": targ_name,
            "type": "biolink:Protein",
        }

        object_node = {
            "id": icd11,
            "icd11": icd11,
            "name": association["clinical_trial"][0]["disease"],
            "type": "biolink:Disease",
        }

        if subject_node["id"] in target_info_d:
            subject_node.update(target_info_d[subject_node["id"]])

        output_dict = {
            "_id": _id,
            "association": association,
            "object": object_node,
            "subject": subject_node,
        }
        yield output_dict


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
            subject_node = {
                "id": line[3].split(":")[1].strip(),
                "name": line[2],
                "type": "biolink:Disease",
            }

            icd_group = [
                (line[3], "ICD-11:"),
                (line[4], "ICD-10:"),
                (line[5], "ICD-9:"),
            ]

            for icd_line, icd_prefix in icd_group:
                icd_value = cleanup_icds(icd_line, icd_prefix)
                icd_key = icd_line.split(":")[0].replace("-", "").strip().lower()
                subject_node[icd_key] = icd_value

            new_subject_node = {k: v for k, v in subject_node.items() if v is not None}

            object_node = {"id": line[0], "type": "biolink:Biomarker"}

            disease_name = line[2].replace(" ", "_")

            biomarker_name = line[1]
            _id = f"{line[0]}_biomarker_for_{disease_name}"

            pattern = r"^(.*\(.*?)(.*)$"
            if "," not in biomarker_name:
                match = re.match(pattern, biomarker_name)
                if match:
                    symbol = match.groups()[1].rstrip(")")
                    object_node["name"] = match.groups()[0].rstrip("(").strip()
                    object_node["symbol"] = symbol
                else:
                    object_node["name"] = biomarker_name.replace(" ", "_")
            else:
                biomarkers = [item.strip() for item in biomarker_name.split(",")]
                object_node["name"] = []
                symbol = []
                for biomarker in biomarkers:
                    match = re.match(pattern, biomarker)
                    if match:
                        symbol.append(match.groups()[1].rstrip(")").strip())
                        object_node["symbol"] = symbol
                        object_node["name"].append(match.groups()[0].rstrip("(").strip())
                    else:
                        object_node["name"].append(biomarker)

            association = {"predicate": "biolink:biomarker_for"}

            output_dict = {
                "_id": _id,
                "association": association,
                "object": object_node,
                "subject": new_subject_node,
            }

            yield output_dict


def load_drug_target_act(file_path):
    """load data from P1-09-Target_compound_activity.txt file

    Keyword arguments:
    file_path: directory stores P1-09-Target_compound_activity.txt file
    """
    activity_file = os.path.join(file_path, "P1-09-Target_compound_activity.txt")
    assert os.path.exists(activity_file)

    target_info_d = {d["target_id"]: d for d in get_target_info(file_path)}

    subject_node = {}
    object_node = {}

    for line in tabfile_feeder(activity_file, header=1):
        subject_node["id"] = line[2]
        subject_node["pubchem_cid"] = line[2]
        subject_node["ttd_id"] = line[1]
        subject_node["type"] = "biolink:Drug"

        object_node["id"] = line[0]
        object_node["type"] = "biolink:Protein"

        if subject_node and object_node:
            if object_node["id"] in target_info_d:
                object_node.update(target_info_d[object_node["id"]])

            _id = f"{subject_node['id']}_associated_with_{object_node['id']}"
            association = {"predicate": "biolink:associated_with"}

            pattern = re.match(r"(IC50|Ki|EC50)\s+(.+)", line[3])
            if pattern:
                association[pattern.groups()[0].lower()] = pattern.groups()[1].replace(" ", "")
            else:
                print(f"{line[3]} pattern does not match.")

            output_dict = {
                "_id": _id,
                "association": association,
                "object": object_node,
                "subject": subject_node,
            }

            yield output_dict

        else:
            print("Subject and Object need to be provided.")


def load_data(file_path):
    """main data load function

    Keyword arguments:
    file_path: directory stores all downloaded data files
    """

    from itertools import chain

    for doc in chain(
            load_drug_target(file_path),
            load_drug_dis_data(file_path),
            load_target_dis_data(file_path),
            load_biomarker_dis_data(file_path),
            load_drug_target_act(file_path),
    ):
        yield doc
