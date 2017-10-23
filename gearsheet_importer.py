__author__ = 'pfftman/lordzouga'

# get data from the gearsheet and put it into the api server

import urllib.request
import urllib.parse

import http.client

import json
import time


def result_is_ok(result):
    return result['result'] == 'ok'


def main():
    # init baasbox
    print('Logging in to backend api...')

    # scopes = ['weaponmods']
    scopes = ['weapontalents', 'playertalents', 'geartalents', 'gearsets', 'weapons', 'weaponmods']

    login_params = json.dumps({'username': 'bot', 'password': 'confedrate', 'appcode': '1234567890'})
    client = http.client.HTTPConnection("localhost:9000")

    client.request('POST', '/login', login_params, {'Content-Type': 'application/json'})
    login_response = client.getresponse()

    login_response = json.loads(login_response.read().decode('utf-8'))

    if not result_is_ok(login_response):
        print("Login to baasbox failed")
        return

    session = login_response['data']["X-BB-SESSION"]
    print('Login successful.')

    # reset the db
    print('resetting the db...')
    reset_params = json.dumps(scopes + ['indexes'])
    client.request('POST', '/plugin/bot.index', reset_params, headers={'Content-Type': 'application/json',
                                                                'X-BB-SESSION': session})
    reset_response = json.loads(client.getresponse().read().decode('utf-8'))

    print('db reset done')

    for scope in scopes:
        pull_data_from_scope(scope, session)


def pull_data_from_scope(scope, session):
    print('Retrieving data from gearsheet..')
    params = urllib.parse.urlencode({'scope': scope, 'format': 'verbose'})
    url = 'https://script.google.com/macros/s/AKfycbwQY10fvbOH0eo3TQ6X-uYe_TfLcWanIdqMKBx7EiXz67Uiem0/exec?%s' \
          % params

    response = urllib.request.urlopen(url).read().decode('utf-8')

    print('Data successfully retrieved.')
    data = json.loads(response)

    client = http.client.HTTPConnection("localhost:9000")
    for item in data:
        #  print(item)
        item['name'] = item['name'].title()  # do this for consistent matching
        item_json = json.dumps(item)
        client.request('POST', '/document/%s' % (scope), item_json,
                       {'Content-Type': 'application/json', 'X-BB-SESSION': session})
        item_add_response = json.loads(client.getresponse().read().decode('utf-8'))

        if result_is_ok(item_add_response):
            print('successfully added an item', item['name'])

        item_id = item_add_response['data']['id']
        # add an index for the talent
        print('indexing...')
        index_json = json.dumps({'name': item['name'], 'collection': scope, 'item_id': item_id})
        client.request('POST', '/document/indexes', index_json,
                       {'Content-Type': 'application/json', 'X-BB-SESSION': session})
        index_add_response = json.loads(client.getresponse().read().decode('utf-8'))

        if result_is_ok(index_add_response):
            print("indexing %s successful" % scope)


def test_plugin():
    print('Logging in to backend api...')
    login_params = json.dumps({'username': 'bot', 'password': 'confedrate', 'appcode': '1234567890'})
    client = http.client.HTTPConnection("localhost:9000")

    client.request('POST', '/login', login_params, {'Content-Type': 'application/json'})
    login_response = client.getresponse()
    login_response = json.loads(login_response.read().decode('utf-8'))

    if login_response['result'] != 'ok':
        print("Login to baasbox failed")
        return

    print('Login successful.')
    session_token = login_response['data']["X-BB-SESSION"]

    client.request('GET', '/plugin/bot.index?%s' % (urllib.parse.urlencode({"param": "Accurate"})),
                   headers={'X-BB-SESSION': session_token})
    index_response = json.loads(client.getresponse().read().decode('utf-8'))

    print(index_response)

# test_plugin()
main()