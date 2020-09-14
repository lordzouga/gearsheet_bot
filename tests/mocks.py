from disco.types.permissions import PermissionValue, Permissions

'''
Create very simple mocks for various classes in py-disco
'''

class User(object):
    '''
    Mock for `disco.types.user.User`
    '''
    def __init__(self, id=345):
        self.id = id
        self.perms = PermissionValue(Permissions.ADMINISTRATOR)

    def set_permission(self, perm):
        self.perms = PermissionValue(perm)

class Message(object):
    '''
    Mock for `disco.types.message.Message`
    '''
    def __init__(self, msg=None):
        self.msg = msg

    def reply(self, msg):
        self.msg = msg

class Guild(object):
    '''
    Mock for `disco.types.guild.Guild`
    '''
    def __init__(self, member=None):
        self.id = 45678
        self.member = member

    def get_permissions(self, user):
        if not self.member: return None
        else:
            return self.member.perms

class Event(object):
    '''
    Mock for `disco.gateway.events.GatewayEvent`
    '''
    author = None
    msg = None
    guild = 0

    def __init__(self):
        self.author = User()
        self.guild = Guild(self.author)
        self.msg = Message()
        