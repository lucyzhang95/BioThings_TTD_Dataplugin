import asyncio
import os.path
import re
from collections import defaultdict

import aiohttp
import aiohttp.client_exceptions
import biothings_client
from biothings.utils.dataload import tabfile_feeder


class UniprotJobIDs:
    """
    The UniprotJobIDs object uses aiohttp and asyncio to obtain uniprot jobIDs
    jobIDs will be used to be included in the url for uniprot ac requests later

    :param file_path: The arg is uniprot source file "P1-01-TTD_target_download.txt"
    :type file_path: str
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.job_ids = []
        self.api_url = "https://rest.uniprot.org"

    def get_uniprot_ac(self):
        """obtain uniprot ac information from "P1-01-TTD_target_download.txt"
        and store in a dictionary {"ttd_target_id": "id", "uniprot_ac": "ac"}

        :return: dictionary object
        """
        uniprot_info_file = os.path.join(self.file_path, "P1-01-TTD_target_download.txt")
        assert os.path.exists(uniprot_info_file)

        ac_dict = None
        for line in tabfile_feeder(uniprot_info_file, header=40):
            if line[1].startswith("TARGETID"):
                ac_dict = {"ttd_target_id": line[2]}
            elif "UNIPROID" in line[1]:
                delimiter_pattern = r"[;/-]"
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
        """generate asyncio co-routine tasks
        to request jobIDs from "https://rest.uniprot.org/idmapping/run"

        :param session: aiohttp.ClientSession used in get_jobIDs() function
        :return: asyncio co-routine tasks
        """
        tasks = []
        ac_l = []
        ac_info = self.get_uniprot_ac()
        for ac_d in ac_info:
            if isinstance(ac_d["uniprot_ac"], list):
                for ac in ac_d["uniprot_ac"]:
                    ac_l.append(ac)
            else:
                ac_l.append(ac_d["uniprot_ac"])

        ac_l = set(ac_l)
        for ac in ac_l:
            data = {"from": "UniProtKB_AC-ID", "to": "UniProtKB", "ids": ac}
            tasks.append(asyncio.create_task(session.post(f"{self.api_url}/idmapping/run", data=data)))
        return tasks

    async def get_jobIds(self):
        """obtain uniprot jobIDs
        from "https://rest.uniprot.org/idmapping/run"
        """
        connector = aiohttp.TCPConnector(verify_ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = self.get_tasks(session)
            responses = await asyncio.gather(*tasks)
            for response in responses:
                self.job_ids.append(await response.json())

    def run_async_task_job_ids(self):
        """execute get_jobIDs() when called and obtain jobID json output

        :return: actual uniport jobIDs (c8e6978b19d064e5e15b9dbc1fed622e2e8d85ac)
        """
        asyncio.run(self.get_jobIds())


class MappedUniprotKbs:
    """
    The MappedUniprotKbs object uses aiohttp and asyncio
    to obtain uniprot json outputs for mapping uniprot ac to kb IDs

    :param job_ids: is used for gathering the jobIDs from class UniprotJobIDs
    :type job_ids: list
    """

    def __init__(self, job_ids):
        self.job_ids = job_ids
        self.uniprot_ac_kb = []
        self.api_url = "https://rest.uniprot.org"

    def get_jobId_mapping_link(self, session):
        """get uniprot json output url using jobIDs for each request

        :param session: asyncio task sessions for next get_mapped_uniprot_kbs function
        :return: asyncio tasks for later use
        """
        tasks = []
        for d in self.job_ids:
            for job_id in d.values():
                get_response = session.get(f"{self.api_url}/idmapping/uniprotkb/results/{job_id}", ssl=False)
                tasks.append(asyncio.create_task(get_response))
        return tasks

    async def get_mapped_uniprot_kbs(self):
        """obtain mapped uniprot ac and kb IDs

        :return: asyncio object contains list of {"uniprot_kb": "kb", "uniprot_ac": "ac"}
        """
        connector = aiohttp.TCPConnector(verify_ssl=False)
        async with aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=300), connector=connector
        ) as session:
            tasks = self.get_jobId_mapping_link(session)
            batch_size = 10
            task_batches = [tasks[i : i + batch_size] for i in range(0, len(tasks), batch_size)]

            for batch in task_batches:
                batch_result = await asyncio.gather(*batch)
                for response in batch_result:
                    try:
                        results = await response.json()
                        if "messages" in results:
                            print(f"{results['url']} results cannot be found on uniprot.")
                        else:
                            try:
                                if results["results"]:
                                    ac = results.get("results")[0]["from"]
                                    kb = results.get("results")[0]["to"]["primaryAccession"]
                                    mapped_dict = {"uniprot_kb": kb, "uniprot_ac": ac}
                                    self.uniprot_ac_kb.append(mapped_dict)
                            except IndexError:
                                print(f"{results.get('failedIds')} cannot be found on uniprot.")
                    except (aiohttp.client_exceptions.ClientOSError, aiohttp.client_exceptions.ServerDisconnectedError):
                        await asyncio.sleep(5)  # To avoid ClientConnectorError: 443 [Operation timed out]


class UniprotMapping:
    """
    The UniprotMapping object executes both jobIDs tasks
    and mapping uniprot ac_kb tasks

    Also, map the uniprot_kb to its corresponding ttd_target_id
    Merge the uniprot_kbs with the same ttd_target_id
    Remove the duplicated uniprot_kbs

    :param file_path: location of the uniprot source file "P1-01-TTD_target_download.txt"
    :type file_path: str
    """

    def __init__(self, file_path):
        self.file_path = file_path

    def run_async_tasks(self):
        """execute both jobIDs asyncio tasks
        and mapping uniprot ac_kb asyncio tasks

        :return: list of dicts {"ttd_target_id":"id", "uniprot": "kb"}
        """
        job_ids_obj = UniprotJobIDs(self.file_path)
        job_ids_obj.run_async_task_job_ids()

        mapped_uniprot_obj = MappedUniprotKbs(job_ids_obj.job_ids)
        asyncio.run(mapped_uniprot_obj.get_mapped_uniprot_kbs())

        mapped_uniprot_kbs = mapped_uniprot_obj.uniprot_ac_kb
        unique_mapped_kbs = set()
        filtered_mapped_kbs = []
        for item in mapped_uniprot_kbs:
            item_tuple = tuple(item.items())
            if item_tuple not in unique_mapped_kbs:
                unique_mapped_kbs.add(item_tuple)
                filtered_mapped_kbs.append(item)

        ac_info = UniprotJobIDs(self.file_path).get_uniprot_ac()
        ac_dict = {d["ttd_target_id"]: d["uniprot_ac"] for d in ac_info}
        final_list = []
        for d in filtered_mapped_kbs:
            for key, value in ac_dict.items():
                if d["uniprot_ac"] in value:
                    d["ttd_target_id"] = key

        merged_uniprot_dict = defaultdict(list)
        for d in filtered_mapped_kbs:
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
                        target_info = {"ttd_target_id": line[2], "uniprotkb": uniprot_dict[line[2]]["uniprot"]}
                    else:
                        target_info = {"ttd_target_id": line[2]}
                elif "TARGTYPE" in line[1]:
                    target_info["target_type"] = line[2].lower()
                elif "BIOCLASS" in line[1]:
                    target_info["bioclass"] = line[2]

            else:
                yield target_info


def mapping_drug_id(file_path):
    """get information from P1-03-TTD_crossmatching.txt file
    information: ttd_drug_id, pubchem_cid, and chembi_id
    map the pubchem_cid or chembi_id to ttd_drug_id

    Keyword arguments:
    file_path: directory stores P1-03-TTD_crossmatching.txt file
    :return: dictionary {"ttd_drug_id": "id", "pubchem_cid": "", "chembi_id": ""}
    """
    drug_mapping_file = os.path.join(file_path, "P1-03-TTD_crossmatching.txt")
    assert os.path.exists(drug_mapping_file)

    drug_mapping_info = None
    for line in tabfile_feeder(drug_mapping_file, header=28):
        if line != ["", "", ""]:  # empty lines in the txt file need to be removed
            if line[1].startswith("TTDDRUID"):
                drug_mapping_info = {"ttd_drug_id": line[2]}
            elif line[1].startswith("PUBCHCID"):
                if ";" in line[2]:
                    drug_mapping_info["pubchem_compound"] = [cid.strip() for cid in line[2].split(";")]
                else:
                    drug_mapping_info["pubchem_compound"] = line[2]
            elif line[1].startswith("ChEBI_ID"):
                drug_mapping_info["chebi"] = line[2].split(":")[1]

            if drug_mapping_info:
                yield drug_mapping_info


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


def get_icd9_11_mondo_mapping(file_path):
    """map the icd9 to icd11 and mondo disease id
    using the input source file P1-08-Biomarker_disease.txt

    Keyword arguments:
    :param file_path: directory stores P1-08-Biomarker_disease.txt
    :return: dictionary with entire {icd11:mondo} ~ 43 key-value pairs
    """
    biomarker_file = os.path.join(file_path, "P1-08-Biomarker_disease.txt")
    assert os.path.exists(biomarker_file)

    icd9_11 = []
    mondo_icd9_dis = biothings_client.get_client("disease")

    for line in tabfile_feeder(biomarker_file, header=16):
        if line:
            icd9 = cleanup_icds(line[5], "ICD-9:")
            icd11 = cleanup_icds(line[3], "ICD-11:")
            if icd9 and icd11:
                if isinstance(icd9, list):
                    for item in icd9:
                        icd9_11.append((icd11, item))
                else:
                    icd9_11.append((icd11, icd9))

    icd9_11 = list(set(icd9_11))
    icd9s = [icd9[1] for icd9 in icd9_11]

    icd9_mondo = mondo_icd9_dis.querymany(icd9s, scopes="mondo.xrefs.icd9", fields="mondo.mondo")
    icd9_mondo = {mondo_d["query"]: mondo_d["_id"] for mondo_d in icd9_mondo if "notfound" not in mondo_d}

    icd11_mondo = {}
    for icd11, icd9 in icd9_11:
        if icd11 not in icd11_mondo and icd9 in icd9_mondo:
            icd11_mondo[icd11] = icd9_mondo[icd9]

    yield icd11_mondo


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
    drug_mapping_info = {d["ttd_drug_id"]: d for d in mapping_drug_id(file_path)}

    all_output_l = []

    for dicts in drug_target_data:
        if dicts["TargetID"] in target_info_d:
            if "uniprotkb" in target_info_d[dicts["TargetID"]]:
                object_node = {"id": f"UniProtKB:{target_info_d[dicts['TargetID']].get('uniprotkb')[0]}"}
            else:
                object_node = {"id": f"ttd_target_id:{dicts['TargetID']}"}
            object_node.update(target_info_d[dicts["TargetID"]])
            object_node["type"] = "biolink:Protein"
        else:
            object_node = {"id": f"ttd_target_id:{dicts['TargetID']}", "type": "biolink:Protein"}

        if dicts["DrugID"] in drug_mapping_info:
            if "chebi" in drug_mapping_info[dicts["DrugID"]]:
                subject_node = {"id": f"CHEBI:{drug_mapping_info[dicts['DrugID']]['chebi']}"}
            elif (
                "pubchem_compound" in drug_mapping_info[dicts["DrugID"]]
                and "pubchem_compound" not in drug_mapping_info[dicts["DrugID"]]
            ):
                subject_node = {"id": f"PUBCHEM.COMPOUND:{drug_mapping_info[dicts['DrugID']]['cid'][0]}"}
            else:
                subject_node = {"id": f"ttd_drug_id:{dicts['DrugID']}"}
            subject_node.update(drug_mapping_info[dicts["DrugID"]])
            subject_node["type"] = "biolink:Drug"

        else:
            subject_node = {"id": f"ttd_drug_id:{dicts['DrugID']}", "type": "biolink:SmallMolecule"}

        _id = f"{subject_node['id'].split(':')[1]}_interacts_with_{object_node['id'].split(':')[1]}"
        association = {"predicate": "biolink:interacts_with", "trial_status": dicts["Highest_status"].lower()}
        output_dict = {"_id": _id, "association": association, "object": object_node, "subject": subject_node}

        drug_moa = dicts["MOA"]
        if drug_moa != ".":
            association["moa"] = drug_moa.lower()

            all_output_l.append(output_dict)

    """
    Remove duplicates with same _id (same pubchem_cid/chembi_id but different ttd_drug_id)
    For example:
    {'_id': '445455_interacts_with_P13631', 'subject':{'ttd_drug_id': 'D0M3LK', 'pubchem_cid': '445455'}}
    {'_id': '445455_interacts_with_P13631' 'subject':{'ttd_drug_id': 'D0MC3J', 'pubchem_cid': '445455'}}
    Only keep the first one
    """

    unique_ids = {}
    filtered_data = []
    for output in all_output_l:
        _id = output["_id"]
        if _id not in unique_ids:
            unique_ids[_id] = True
            filtered_data.append(output)

    for item in filtered_data:
        yield item


def load_drug_dis_data(file_path):
    """load data from P1-05-Drug_disease.txt file
        and clean up the data

    Keyword arguments:
    file_path: directory stores 1-05-Drug_disease.txt file
    """
    drug_dis_file = os.path.join(file_path, "P1-05-Drug_disease.txt")
    assert os.path.exists(drug_dis_file)

    # dictionary contains drug chembi_id and pubchem_cid info
    drug_mapping_info = {d["ttd_drug_id"]: d for d in mapping_drug_id(file_path)}

    # To make use of the icd11 and mondo mapping must put the obj dictionary into a list
    # Or it will only iterate once not all dictionary keys
    icd11_mondo = [d for d in get_icd9_11_mondo_mapping(file_path)]

    drug_dis_list = []
    all_output_l = []

    drug_id = None
    drug_name = None

    for line in tabfile_feeder(drug_dis_file, header=22):
        # skip the empty lines in input data file
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
                    _id = f"{drug_id}__{drug_name}__{icd11}"
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
        drug_id = _id.split("__")[0]
        drug_name = _id.split("__")[1]
        icd11 = _id.split("__")[2]

        association = {"predicate": "biolink:treats", "clinical_trial": trial_list}

        object_node = {
            "id": None,
            "icd11": icd11,
            "name": association["clinical_trial"][0]["disease"],
            "type": "biolink:Disease",
        }

        for d in icd11_mondo:
            if icd11 in d:
                object_node["id"] = d[icd11]
                object_node["mondo"] = d[icd11].split(":")[1]

        if object_node["id"] is None:
            object_node["id"] = f"ICD11:{icd11}"

        if drug_id in drug_mapping_info:
            if "chebi" in drug_mapping_info[drug_id]:
                subject_node = {"id": f"CHEBI:{drug_mapping_info[drug_id]['chebi']}"}
            elif (
                "pubchem_compound" in drug_mapping_info[drug_id]
                and "pubchem_compound" not in drug_mapping_info[drug_id]
            ):
                subject_node = {"id": f"PUBCHEM.COMPOUND:{drug_mapping_info[drug_id]['pubchem_compound'][0]}"}
            else:
                subject_node = {"id": f"ttd_drug_id:{drug_id}"}
            subject_node.update(drug_mapping_info[drug_id])
            subject_node["name"] = drug_name
            subject_node["type"] = "biolink:Drug"
        else:
            subject_node = {"id": f"ttd_drug_id:{drug_id}", "type": "biolink:SmallMolecule"}

        output_dict = {
            "_id": f"{subject_node['id'].split(':')[1]}_treats_{object_node['id'].split(':')[1]}",
            "association": association,
            "object": object_node,
            "subject": subject_node,
        }

        all_output_l.append(output_dict)

    """
    Remove duplicates with same _id (same pubchem_cid/chembi_id but different ttd_drug_id)
    For example:
    {'_id': '143117_treats_2C25.Y', 'subject':{'ttd_drug_id': 'D04DYC', 'chembi_id': '143117'}}
    {'_id': '143117_treats_2C25.Y' 'subject':{'ttd_drug_id': 'D04DYC', 'chembi_id': '143117'}}
    Only keep the first one
    """

    unique_ids = {}
    filtered_data = []
    for output in all_output_l:
        _id = output["_id"]
        if _id not in unique_ids:
            unique_ids[_id] = True
            filtered_data.append(output)

    for item in filtered_data:
        yield item


def load_target_dis_data(file_path):
    """load data from P1-06-Target_disease.txt file
        and clean up the data

    Keyword arguments:
    file_path: directory stores P1-06-Target_disease.txt file
    """
    target_dis_file = os.path.join(file_path, "P1-06-Target_disease.txt")
    assert os.path.exists(target_dis_file)

    target_info_d = {d["ttd_target_id"]: d for d in get_target_info(file_path)}
    icd11_mondo = [d for d in get_icd9_11_mondo_mapping(file_path)]

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
                        "_id": f"{targ_id}__{targ_name}__{icd11}",
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
        targ_id = _id.split("__")[0]
        targ_name = _id.split("__")[1]
        icd11 = _id.split("__")[2]

        if targ_id in target_info_d:
            if "uniprotkb" in target_info_d[targ_id]:
                subject_node = {"id": f"UniProtKB:{target_info_d[targ_id].get('uniprotkb')[0]}"}
            else:
                subject_node = {"id": f"ttd_target_id:{targ_id}"}
            subject_node.update(target_info_d[targ_id])
            subject_node["name"] = targ_name
            subject_node["type"] = "biolink:Protein"
        else:
            subject_node = {"id": f"ttd_target_id:{targ_id}", "name": targ_name, "type": "biolink:Protein"}

        association = {
            "predicate": "biolink:target_for",
            "clinical_trial": trial_list,
        }

        object_node = {
            "id": None,
            "icd11": icd11,
            "name": association["clinical_trial"][0]["disease"],
            "type": "biolink:Disease",
        }

        for d in icd11_mondo:
            if icd11 in d:
                object_node["id"] = d[icd11]
                object_node["mondo"] = d[icd11].split(":")[1]

        if object_node["id"] is None:
            object_node["id"] = f"ICD11:{icd11}"

        _id = f"{subject_node['id'].split(':')[1]}_target_for_{object_node['id'].split(':')[1]}"

        output_dict = {
            "_id": _id,
            "association": association,
            "object": object_node,
            "subject": subject_node,
        }
        yield output_dict


def load_biomarker_dis_data(file_path):
    """load data from P1-08-Biomarker_disease.txt file

    Keyword arguments:
    file_path: directory stores P1-08-Biomarker_disease.txt file
    """
    biomarker_file = os.path.join(file_path, "P1-08-Biomarker_disease.txt")
    assert os.path.exists(biomarker_file)

    icd11_mondo = [d for d in get_icd9_11_mondo_mapping(file_path)]

    for line in tabfile_feeder(biomarker_file, header=16):
        if line:
            subject_node = {
                "id": None,
                "name": line[2],
                "type": "biolink:Disease",
            }

            icd11 = line[3].split(":")[1].strip()
            for d in icd11_mondo:
                if icd11 in d:
                    subject_node["id"] = d[icd11]
                    subject_node["mondo"] = d[icd11].split(":")[1]

                if subject_node["id"] is None:
                    subject_node["id"] = f"ICD11:{icd11}"

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

            biomarker_name = line[1]
            _id = f"{line[0]}_biomarker_for_{subject_node['id'].split(':')[1]}"

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

    target_info_d = {d["ttd_target_id"]: d for d in get_target_info(file_path)}

    subject_node = {}

    for line in tabfile_feeder(activity_file, header=1):
        subject_node["id"] = f"PUBCHEM.COMPOUND:{line[2]}"
        subject_node["pubchem_compound"] = line[2]
        subject_node["ttd_drug_id"] = line[1]
        subject_node["type"] = "biolink:SmallMolecule"

        if line[0] in target_info_d:
            if "uniprotkb" in target_info_d[line[0]]:
                object_node = {"id": f"UniProtKB:{target_info_d[line[0]].get('uniprotkb')[0]}"}
            else:
                object_node = {"id": f"ttd_target_id:{line[0]}"}
            object_node.update(target_info_d[line[0]])
            object_node["type"] = "biolink:Protein"
        else:
            object_node = {"id": f"ttd_target_id:{line[0]}", "type": "biolink:Protein"}

        if subject_node and object_node:
            _id = f"{subject_node['id'].split(':')[1]}_interacts_with_{object_node['id'].split(':')[1]}"
            association = {"predicate": "biolink:interacts_with"}

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

    from itertools import chain, groupby
    from operator import itemgetter

    def merge_dicts(dicts):
        """merge dictionaries with the same _id
        load_drug_target() function and load_drug_target_act() has 11198 duplicated _ids

        Keyword arguments:
        dicts: itertools chain to iterate through all dictionaries from all above load functions
        """
        merged_docs = {}
        sorted_dicts = sorted(dicts, key=itemgetter("_id"))
        grouped_dicts = groupby(sorted_dicts, key=itemgetter("_id"))

        for _id, group in grouped_dicts:
            merged_doc = {}
            for doc in group:
                for key, value in doc.items():
                    if key in merged_doc:
                        if "association" in key:
                            value.update(value)
                            merged_doc[key] = value
                        else:
                            pass
                    else:
                        merged_doc[key] = value

            merged_docs[_id] = merged_doc

        return merged_docs.values()

    dicts = chain(
        load_drug_target(file_path),
        load_drug_dis_data(file_path),
        load_target_dis_data(file_path),
        load_biomarker_dis_data(file_path),
        load_drug_target_act(file_path),
    )

    merged_dicts = merge_dicts(dicts)
    yield from merged_dicts
