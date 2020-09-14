from functools import wraps

# workaround to import from parent directory
import sys 
sys.path.append('..')

import config
import util

from plugins import bot
from holster.enum import Enum, EnumAttr
from unittest.mock import Mock, patch
from mocks import Event
from disco.types.permissions import Permissions

from nose.tools import assert_is_none, assert_list_equal, assert_true

def test_protect_from_users():
    event = Event()
    main_bot = bot.GearSheetPlugin(None, None, debug=True)

    config.vendors_command_user_filter["foo"] = 345 
    main_bot._command_ping(event)
    assert_true(event.msg.msg == None)

    # reset event
    event = Event()

    assert_is_none(event.msg.msg)

    config.vendors_command_user_filter["foo"] = 5
    main_bot._command_ping(event)
    assert_true(event.msg.msg == "Pong!")

@util.admin_only()
def dummy_for_admin_test(obj, event):
    return True

def test_admin_only():
    event = Event()
    
    # test with a non-admin role first
    event.author.set_permission(Permissions.CHANGE_NICKNAME)
    assert_is_none(dummy_for_admin_test(None, event))

    # test with admin role
    event.author.set_permission(Permissions.ADMINISTRATOR)
    assert_true(dummy_for_admin_test(None, event))

