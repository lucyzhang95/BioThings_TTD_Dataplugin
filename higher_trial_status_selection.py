from TTD_parser import load_drug_dis_data

filepath = "/Users/lucyzhang1116/Documents/biothings_TTD_plugin/Data"
drug_dis_data = load_drug_dis_data(filepath)

id_once = []
id_duplicate = []
for d in drug_dis_data:
    _ids = d["_id"]

    if _ids not in id_once:
        id_once.append(_ids)
    else:
        print(_ids)

filepath = "/Users/lucyzhang1116/Documents/biothings_TTD_plugin/Data"
drug_dis_data = load_drug_dis_data(filepath)

with open("duplicated_drug_disease.txt", "r") as file:
    drug_dis = file.readlines()
    drug_dis_strip = [items.strip("\n") for items in drug_dis]
    for d in drug_dis_data:
        if d["_id"] in drug_dis_strip:
            dict = {d["_id"]: d["subject"]["trial_status"]}
            print(dict)


status_lst = ["Withdrawn from market", "Investigative", "Patented", "NDA filed", "Application Submitted",
              "Clinical trial", "Phase 1", "Phase 2", "Phase 1/2", "Phase 3", "Phase 2/3", "Approved"]

drug_lst = [{'D00GOV_treats_2C25.Y': 'Approved'}, {'D00GOV_treats_2C25.Y': 'Phase 3'},
            {'D00DYI_treats_ED61.0': 'Patented'}, {'D00DYI_treats_ED61.0': 'Patented'},
            {'D00PMB_treats_2E66.1': 'Phase 3'}, {'D00PMB_treats_2E66.1': 'Phase 2'}]

higher_status_dict = {}
trial_pos = {}
new_dict = {}

for d in drug_lst:
    for keys in d.keys():
        if keys == keys:
            if d.get(keys) in status_lst:
                index = status_lst.index(d.get(keys))
                trial_pos[keys] = index

                for k, v in trial_pos.items():
                    if k in higher_status_dict and v >= higher_status_dict[k]:
                        higher_status_dict[k] = v
                    elif k not in higher_status_dict:
                        higher_status_dict[k] = v

print(higher_status_dict)

for k,v in higher_status_dict.items():
    trial_status = status_lst[v]
    new_dict[k] = trial_status

print(new_dict)

