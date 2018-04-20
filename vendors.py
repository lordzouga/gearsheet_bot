__author__ = 'pfftman'

import urllib.parse
import urllib.request
import json
import requests

CATEGORIES = ['gear-mods', 'weapon-mods', 'weapons', 'recommendations', 'gear']
BACKEND_HOST = "http://localhost:9000"
SESSION_HEADER = 'X-BB-SESSION'
VENDOR_HOST = 'www.rubenalamina.mx'
CATEGORY_HASHES = dict()
PLUGIN_PATH = "/plugin/vendors.index"
VENDORS_INDEX_PATH = "/document/vendors-index"

def login_to_backend():
    login = {"username": "bot", "password": "confedrate", "appcode": "gearsheet"}
    login_url = BACKEND_HOST + "/login"
    loginval = requests.post(login_url, json=login)

    if loginval.json()['result'] != 'ok':
        print('Login Failed')
        return ''
    else:
        print("Login Successful")
        return loginval.json()['data'][SESSION_HEADER]

def get_data_from_category(category):
    url = 'http://' + VENDOR_HOST + '/division/%s.json' % category
    response = urllib.request.urlopen(url).read().decode('utf-8')

    # print('Data successfully retrieved.')
    return json.loads(response)

def result_is_ok(result):
    return result.json()['result'] == 'ok'

def get_attributes_from_gear(gear):
    major = gear['major']
    minor = gear['minor']

    return parse_attributes([major, minor])

def parse_attributes(raw_attr):
    attrs = []

    for k in raw_attr:
        if k.strip() != "-":
            split_item = k.split("<br/>")
            for attr in split_item:
                i = attr.find(" ") + 1 # find the index of the first space
                attrs.append(attr[i:].strip().lower())
    
    return attrs


def convert_to_dict(items):
    temp = dict()

    # keys = [k for k in [i for i in items if i != "name"]]

    for item in items:
        temp[item["name"].lower()] = [item[w].lower() for w in item.keys() if w != "name"and w != "@version" and w != "@rid"]
    
    return temp

def update():
    session = login_to_backend()
    if not session:
        return

    # reset the vendors index
    header = {SESSION_HEADER: session}
    res = requests.post(BACKEND_HOST + PLUGIN_PATH, json=["vendors-index"], headers=header)

    if result_is_ok(res):
        print("index reset is successful")
    else: 
        print("index reset unsuccessful", res)
        return
    
    for category in CATEGORIES:
        data = get_data_from_category(category)
        print("Got data from %s category and it has %s items" % (category, len(data)))

        hash_value = hash(json.dumps(data))
        if True:#not (category in CATEGORY_HASHES.keys() and CATEGORY_HASHES[category] == hash_value):
            # reset the data for the scope
            collection_name = 'vendors-' + category
            scope_to_reset = [collection_name]
            reset_resp = requests.post(BACKEND_HOST + PLUGIN_PATH, json=scope_to_reset, headers=header)
            
            weapons_param = { 
                "fields": "name,variant,type"
            }
            weapons_data = requests.get(BACKEND_HOST + '/document/weapons', params=weapons_param, headers=header).json()
            weapons_data = convert_to_dict(weapons_data["data"])

            weapon_mods_param = {
                "fields": "name,category,Mod_Type"
            }

            weapon_mods_data = requests.get(BACKEND_HOST + '/document/weaponmods', params=weapon_mods_param, headers=header).json()
            weapon_mods_data = convert_to_dict(weapon_mods_data['data'])
 
            if result_is_ok(reset_resp):
                print("reset of %s table successful" % category)

                for item in data:
                    if item:
                        category_path = '/document/vendors-%s' % category
                        item_add_resp = requests.post(BACKEND_HOST + category_path, json=item, headers=header)

                        if result_is_ok(item_add_resp):
                            item_id = item_add_resp.json()["data"]['id']
                            
                            ### ADD WEAPONS ###
                            if category == 'weapons':
                                talents = [item['talent1'].strip().lower(), item['talent2'].strip().lower(), item['talent3'].strip().lower()]
                                weapon_name = item['name'].lower()

                                index_data = {
                                    "name": weapon_name, 
                                    "collection": collection_name, 
                                    "item_id": item_id,
                                    "attributes": talents
                                }

                                requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)
                                
                                if weapon_name in weapons_data.keys():
                                    index_data["name"] = weapons_data[weapon_name][0] # weapon variant
                                    requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)

                                    index_data["name"] = weapons_data[weapon_name][1] # weapon type
                                    requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)
                                else:
                                    print(weapon_name + " not found")
                                
                                # delete the attributes key because talents shouldn't have attributes
                                del index_data["attributes"]

                                for talent in talents:
                                    if talent != '-':
                                        index_data['name'] = talent.lower()
                                        requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)
                                # print("added talent for weapon..")

                            ### ADD GEAR ###
                            elif category == 'gear':
                                attrs = get_attributes_from_gear(item)
                                pieces = ["chest", "gloves", "knee pads", "holster", "mask", "backpack"]
                                gear_name = item['name'].lower()

                                index_data = {"name": gear_name,
                                    "collection": collection_name, 
                                    "item_id": item_id,
                                    "attributes": attrs }

                                requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)

                                type = [t for t in pieces if t in gear_name] # must have a value
                                type = type[0].strip() if len(type) > 0 else "" # for safety in case someone fucks up
                                gearset = gear_name.replace(type, "").strip()
                                
                                if type:
                                    # print("indexing a %s..." % type)
                                    index_data["name"] = type

                                    requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)

                                    # print("indexing a %s..." % gearset)
                                    index_data['name'] = gearset

                                    requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)

                                # delete the attributes item because attr shouldn't have attributes
                                del index_data["attributes"]

                                for attr in attrs:
                                    index_data['name'] = attr.lower()
                                    requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)
                        
                                # print("added attributes for gear")
                            elif category == "gear-mods":
                                mod_name = item["name"].lower()

                                attr = item["attribute"]
                                space = attr.find(" ") + 1 # find the first index of whitespace
                                attrs = [attr[space:].strip().lower()]

                                index_data = {
                                    "name": mod_name,
                                    "collection": collection_name,
                                    "item_id": item_id,
                                    "attributes": attrs
                                }

                                requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)

                                index_data["name"] = "mod"
                                requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)

                                if item["type"] == "purple-mod":
                                    index_data["name"] = "purple mod"
                                    requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)
                                
                                del index_data["attributes"]

                                index_data["name"] = attrs[0]
                                requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)
                                
                            elif category == "weapon-mods":
                                mod_name = item["name"].lower()
                                attrs = parse_attributes([item["attributes"]])

                                index_data = {
                                    "name": mod_name,
                                    "collection": collection_name,
                                    "item_id": item_id,
                                    "attributes": attrs
                                }

                                requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)

                                if mod_name in weapon_mods_data.keys():
                                    index_data["name"] = weapon_mods_data[mod_name][0]
                                    requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)

                                    index_data["name"] = weapon_mods_data[mod_name][1]
                                    requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)

                                index_data["name"] = "weapon mod"
                                requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)

                                del index_data["attributes"]

                                for attr in attrs:
                                    index_data["name"] = attr
                                    requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)
                        else:
                            print("adding item from %s category failed" % category)
                
                CATEGORY_HASHES[category] = hash_value
            else:
                print("reset of %s table failed. skipped" % category)
        else:
            print("No changes found for %s category" % category)

        print(hash_value)
        # len(data)

if __name__ == '__main__':
    update()