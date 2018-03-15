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

    attrs = []

    for k in [major, minor]:
        if k.strip() != "-":
            split_item = k.split("<br/>")
            for attr in split_item:
                i = attr.find(" ") + 1 # find the index of the first space
                attrs.append(attr[i:].strip())

    return attrs
    
def main():
    session = login_to_backend()
    if not session:
        return

    # reset the vendors index
    header = {SESSION_HEADER: session}
    res = requests.post(BACKEND_HOST + PLUGIN_PATH, json=["vendors-index"], headers=header)

    if result_is_ok(res):
        print("index reset is successful")
    else: 
        print("index reset unsuccessful")
        return
    
    for category in CATEGORIES:
        data = get_data_from_category(category)
        print("Got data from %s category and it has %s items" % (category, len(data)))

        hash_value = hash(json.dumps(data))
        if not (category in CATEGORY_HASHES.keys() and CATEGORY_HASHES[category] == hash_value):
            # reset the data for the scope
            collection_name = 'vendors-' + category
            scope_to_reset = [collection_name]
            reset_resp = requests.post(BACKEND_HOST + PLUGIN_PATH, json=scope_to_reset, headers=header)

            if result_is_ok(reset_resp):
                print("reset of %s table successful" % category)

                for item in data:
                    if item:
                        category_path = '/document/vendors-%s' % category
                        item_add_resp = requests.post(BACKEND_HOST + category_path, json=item, headers=header)

                        if result_is_ok(item_add_resp):
                            item_id = item_add_resp.json()["data"]['id']
                            index_data = {"name": item['name'].lower(), "collection": collection_name, "item_id": item_id}
                            requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)

                            if category == 'weapons':
                                talents = [item['talent1'].strip(), item['talent2'].strip(), item['talent3'].strip()]
                                
                                for talent in talents:
                                    if talent != '-':
                                        index_data['name'] = talent.lower()
                                        requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)
                                
                                # print("added talent for weapon..")
                            elif category == 'gear':
                                attrs = get_attributes_from_gear(item)
                                
                                for attr in attrs:
                                    index_data['name'] = attr.lower()
                                    requests.post(BACKEND_HOST + VENDORS_INDEX_PATH, json=index_data, headers=header)
                                
                                # print("added attributes for gear")
                        else:
                            print("adding item from %s category failed" % category)
                
                CATEGORY_HASHES[category] = hash_value
            else:
                print("reset of %s table failed. skipped" % category)
        else:
            print("No changes found for %s category" % category)

        print(hash_value)
        # len(data)

main()