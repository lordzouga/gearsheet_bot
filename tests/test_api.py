import pytest
import sys 
sys.path.append('..')

import config

from unittest.mock import Mock, patch
from nose.tools import assert_is_none, assert_list_equal, assert_true
from functools import wraps

from api import BaasBoxBackend

token = "mytoken"

@patch('api.requests.get')
def test_make_request_when_response_is_ok(mock_get):
    # Configure the mock to return a response with an OK status code.

    backend = BaasBoxBackend(token)
    mock_get.return_value.ok = True

    todos = {
        "result": "ok",
        "data": [
            {
            'userId': 1,
            'id': 1,
            'title': 'Make the bed',
            'completed': False
            }
        ]
    }

    mock_get.return_value = Mock()
    mock_get.return_value.json.return_value = todos

    # Call the service, which will send a request to the server.
    response = backend.make_request(config.host + config.gearsheet_plugin_index_url, {"param": "responsive"})

    # If the request is sent successfully, then I expect a response to be returned.
    assert_list_equal(response, todos["data"])

@patch('api.requests.get')
def test_make_request_when_response_is_none(mock_get):
    backend = BaasBoxBackend(token)
    mock_get.return_value.ok = False
    
    todos = []

    response = backend.make_request(config.host + config.gearsheet_plugin_index_url, {"param": "responsive"})
    assert_list_equal(response, todos)

@patch('api.requests.post')
def test_login_when_response_is_ok(mock_post):
    
    backend = BaasBoxBackend()
    new_token = "newtoken"
    mock_post.return_value.ok = True

    value = {
        "result": "ok",
        "data":
            {
                'X-BB-SESSION': new_token
            }
        }

    mock_post.return_value = Mock()
    mock_post.return_value.json.return_value = value
    
    gen_token = backend.login()
    assert_true(new_token == gen_token)
