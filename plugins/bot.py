from disco.bot import Plugin
from disco.types.message import MessageEmbed  # We need this to create the embed

import urllib.request
import urllib.parse
import http.client
import logging
from fuzzywuzzy import fuzz


import json
import time

import util

class GearSheetPlugin(Plugin):
    session = ""
    conn = None
    WEAPON_TALENTS = 'weapontalents'
    PLAYER_TALENTS = 'playertalents'
    GEAR_TALENTS = 'geartalents'
    GEAR_SETS = 'gearsets'
    WEAPONS = 'weapons'
    WEAPON_MODS = 'weaponmods'
    EXOTIC_GEARS = 'exoticgears'
    GEAR_ATTRIBUTES = 'gearattributes'
    names = {}
    logger = None

    def __init__(self, bot, config):
        super().__init__(bot, config)


        print('Logging in to backend api...')
        login_params = json.dumps({'username': 'bot', 'password': 'confedrate', 'appcode': 'gearsheet'})
        conn = http.client.HTTPConnection("localhost:9000")

        conn.request('POST', '/login', login_params, {'Content-Type': 'application/json'})
        login_response = conn.getresponse()
        login_response = json.loads(login_response.read().decode('utf-8'))

        if login_response['result'] != 'ok':
            print("Login to baasbox failed")
            return

        print('Login successful.')
        self.session = login_response['data']["X-BB-SESSION"]

        # get a list of all indexed names
        params = urllib.parse.urlencode({'fields': 'name'})
        conn.request('GET', '/document/indexes?%s' % params, headers={'X-BB-SESSION': self.session})
        res = json.loads(conn.getresponse().read().decode('utf-8'))
        self.names = {i['name'] for i in res['data']}

        conn.close()

        # init logging
        self.logger = logging.getLogger('gearsheet_bot')
        self.logger.setLevel(logging.INFO)

        fh = logging.FileHandler('access.log')
        fh.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
        fh.setFormatter(formatter)

        self.logger.addHandler(fh)


    @Plugin.command('ping')
    def command_ping(self, event):

        event.msg.reply('Pong!')

    @Plugin.command('sheet')
    @Plugin.command('gearsheet')
    def command_talents(self, event):
        if len(event.args) > 0:
            param = ' '.join(event.args).lower()

            if param in util.aliases.keys():
                param = util.aliases[param].lower()

            # start_time = time.time()
            conn = http.client.HTTPConnection("localhost:9000")
            conn.request('GET', '/plugin/bot.index?%s' % (urllib.parse.urlencode({"param": param})),
                            headers={'X-BB-SESSION': self.session})

            response = conn.getresponse().read().decode('utf-8')
            # time_diff = time.time() - start_time

            self.logger.info("%s - %s - %s - %s" % (str(event.author).replace(" ", "_"), event.guild.name.replace(" ", "_"), event.guild.id, param))

            response = json.loads(response)
            if response['result'] != 'ok':
                matches = [("**%s**" % i).title() for i in self.names if fuzz.partial_ratio(param, i) > 80]

                if len(matches) > 0:
                    match_str = "this %s" % ', '.join(matches) if len(matches) == 1 else \
                        "any of these %s" % ', '.join(matches)
                    text = "Did you mean to search for %s?" % \
                           match_str
                    event.msg.reply('%s' % text)
                else:
                    event.msg.reply('```item not found```')

                return

            for item in response['data']:
                collection_name = item['@class']

                embed = None
                if collection_name == self.WEAPON_TALENTS:
                    embed = self.render_weapon_talent(item)
                elif collection_name == self.PLAYER_TALENTS:
                    embed = self.render_player_talent(item)
                elif collection_name == self.GEAR_TALENTS:
                    embed = self.render_gear_talent(item)
                elif collection_name == self.GEAR_SETS:
                    embed = self.render_gearset(item)
                elif collection_name == self.WEAPONS:
                    embed = self.render_weapon(item)
                elif collection_name == self.WEAPON_MODS:
                    embed = self.render_weapon_mods(item)
                elif collection_name == self.EXOTIC_GEARS:
                    embed = self.render_exotic_gear(item)
                elif collection_name == self.GEAR_ATTRIBUTES:
                    embed = self.render_gear_attribute(item)

                event.msg.reply(embed=embed)

            conn.close()

    def render_weapon_talent(self, talent):
        embed = MessageEmbed()
        # embed.set_author(name='GearSheet')

        embed.title = talent['name']
        embed.description = talent['description']

        req = talent['requirements']['34']
        req_str = '**electronics**: %s, **firearms**: %s, **stamina**: %s' % \
                  ('none' if req['electronics'] == 0 else req['electronics'],
                   'none' if req['firearms'] == 0 else req['firearms'],
                   'none' if req['stamina'] == 0 else req['stamina'])

        embed.add_field(name='Rolls On', value=', '.join(talent['rollsOn']), inline=True)
        embed.add_field(name='Requirements', value=req_str, inline=True)

        if 'note' in talent.keys():
            embed.set_footer(text=talent['note'])

        return embed

    def render_player_talent(self, talent):
        embed = MessageEmbed()

        embed.title = talent['name']
        embed.description = talent['description']

        embed.add_field(name='Type', value=talent['type'], inline=True)
        embed.add_field(name='Benefits', value=talent['benefit'], inline=True)

        return embed

    def render_gear_talent(self, talent):
        embed = MessageEmbed()

        embed.title = talent['name']
        embed.description = talent['description']

        embed.set_footer(text='Rolls on %s' % talent['slot'])
        return embed

    def render_gearset(self, gearset):
        embed = MessageEmbed()

        embed.title = gearset['name']

        embed.add_field(name='2 piece bonus', value=gearset['2'], inline=True)
        embed.add_field(name='3 piece bonus', value=gearset['3'], inline=True)
        embed.add_field(name='4 piece bonus', value=gearset['4'])
        embed.add_field(name='5 piece bonus', value=gearset['5'], color='489979')
        embed.add_field(name='6 piece bonus', value=gearset['6'])

        embed.set_footer(text="added in patch %s" % gearset['patch'])
        embed.color = '52377'

        return embed

    def render_weapon(self, weapon):
        self.normalize(weapon)
        embed = MessageEmbed()

        embed.title = weapon['name']

        embed.add_field(name='Type', value=weapon['type'], inline=True)
        embed.add_field(name='Variant', value=weapon['variant'], inline=True)
        embed.add_field(name='RPM', value=weapon['rpm'], inline=True)

        embed.add_field(name='Scaling', value=weapon['scaling'], inline=True)
        embed.add_field(name='Magazine Size', value=weapon['MagSize'], inline=True)
        embed.add_field(name='Optimal Range(m)', value=weapon['OptimalRange'], inline=True)

        embed.add_field(name='Reload Speed(ms)', value=weapon['ReloadSpeed'], inline=True)
        embed.add_field(name='Headshot Multiplier', value=weapon['HeadshotMultiplier'], inline=True)
        embed.add_field(name='Native Bonus', value=weapon['WeaponBonus'], inline=True)

        embed.add_field(name='Bonus', value=weapon['Bonus'], inline=True)

        damageStr = "%s - %s" % (weapon['256']['min'], weapon['256']['max'])

        embed.add_field(name='Base Damage', value=damageStr, inline=True)

        if 'modCompat' in weapon.keys():
            compat = ', '.join(weapon['modCompat']['compat'])
            embed.add_field(name='Compatible Mods', value=compat)

            if 'note' in weapon['modCompat'].keys():
                embed.set_footer(text="%s" % weapon['modCompat']['note'])

        if 'talent' in weapon.keys():
            description = weapon['talent']['description']
            embed.description = description

        return embed

    def normalize(self, item):  # don't give empty params to bot embed
        for i in item.keys():
            if type(item[i]) is str and len(item[i]) == 0:
                item[i] = '-'

    def render_weapon_mods(self, mod):
        embed = MessageEmbed()
        key_names = {"Mod_Category", "name", "Primary_Attribute", "Mod_Type", "Crit_Chance",
                     "Crit_Damage", "Headshot_Damage", "Accuracy", "Stability", "Reload_Speed",
                    "Rate_Of_Fire", "Optimal_Range", "Magazine_Size", "Decreased_Threat", "Increased_Threat"}

        for key in mod.keys():
            if key == 'name':
                embed.title = mod['name']
            elif key in key_names:
                val_str = ", ".join(mod[key]) if type(mod[key]) is list else mod[key]
                embed.add_field(name=key.replace("_", " "), value=val_str, inline=True)

        embed.set_footer(text="All mods will roll their Primary Attributes, "
                              "as well as an additional 2 attributes")

        return embed

    def render_exotic_gear(self, exotic_gear):
        embed = MessageEmbed()

        embed.title = exotic_gear['name']
        embed.description = exotic_gear['description']

        return embed

    def render_gear_attribute(self, gear_attribute):
        embed = MessageEmbed()

        key_names = ["type", "name", "Minimum_Total", "Mask", "Body_Armor", "Backpack", "Gloves", "Knee_Pads", "Holster",
                     "Maximum_Total", "Max_With_Gear_Mods"]

        for key in gear_attribute.keys():
            if key == 'name':
                embed.title = gear_attribute[key]
            elif key in key_names:
                val = gear_attribute[key]
                embed.add_field(name=key.replace("_", " "), value=val, inline=True)

        return embed
