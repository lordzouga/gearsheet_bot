from disco.bot import Plugin
from disco.types.message import MessageEmbed  # We need this to create the embed

import urllib.request
import urllib.parse
import http.client
import logging
from fuzzywuzzy import fuzz
import arrow

import json
import time

import util
import requests
import vendors

from gevent.lock import BoundedSemaphore
from datetime import datetime

BACKEND_HOST = "http://localhost:9000"
SESSION_HEADER = 'X-BB-SESSION'
VENDOR_WEAPONS = 'weapons'
VENDOR_WEAPON_MODS = 'weapon-mods'
VENDOR_GEAR_MODS = 'gear-mods'
VENDOR_RECOMMENDATIONS = 'recommendations'
VENDOR_GEAR = 'gear'
scopes = ['weapontalents', 'playertalents', 'geartalents', 'gearsets', 'weapons', 'weaponmods', 'exoticgears',
              'gearattributes']

def get_collection_name(name):
    return "vendors-%s" % name

def remove_duplicates(data):
    temp = set()
    stripped = []

    for i in data:
        if i['id'] not in temp:
            temp.add(i['id'])
            stripped.append(i)
    
    return stripped

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
    vendor_names = {}
    logger = None
    lock = None

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

        vendors_param = { "fields": "name" }
        response = requests.get(BACKEND_HOST + '/document/vendors-index', params=vendors_param, headers={SESSION_HEADER: self.session})
        self.vendor_names = {i['name'] for i in response.json()['data']}

        # init logging
        self.logger = logging.getLogger('gearsheet_bot')
        self.logger.setLevel(logging.INFO)

        fh = logging.FileHandler('access.log')
        fh.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
        fh.setFormatter(formatter)

        self.logger.addHandler(fh)
        
        self.lock = BoundedSemaphore(1)


    @Plugin.command('ping')
    def command_ping(self, event):
        event.msg.reply('Pong!')

    def log_it(self, event, param, command):
        if event.author.id not in [195168390476726272]:
            self.logger.info("%s - %s - %s - %s - %s" % (command, str(event.author).replace(" ", "_"), event.guild.name.replace(" ", "_"), event.guild.id, param))

    @Plugin.command('g')
    @Plugin.command('s')
    @Plugin.command('sheet')
    @Plugin.command('gearsheet')
    def command_talents(self, event):
        if len(event.args) > 0:
            param = ' '.join(event.args).lower()

            if param == 'help':
                help_text = '''I can only perform simple searches for **The Division** related items\n
Example: to find out what *Responsive* talent does, use `!gearsheet responsive`\n
Popular community nicknames for items are also supported.\n
**PRO TIP**: `!sheet responsive` will also work.

My reddit thread: https://goo.gl/638vpi.

**Credit** to @Pfftman#6620 | /u/pfftman | PSN: pfftman'''

                self.log_it(event, param, "gearsheet")
                event.msg.reply(help_text)
                return

            if param in util.aliases.keys():
                param = util.aliases[param].lower()
            
            if param in scopes and param != 'weapons':
                self.log_it(event, param, "gearsheet")
                query = {
                    'fields': 'name',
                    'orderBy': 'name'
                }
                names = requests.get(BACKEND_HOST + "/document/%s" % param, query, headers={SESSION_HEADER: self.session}).json()
                # print(names)
                name_list = ['`' + i["name"] + '`' for i in names["data"]]

                event.msg.reply('there are **%s items**' % len(name_list))
                event.msg.reply(",  ".join(name_list))

                return
            
            # start_time = time.time()
            conn = http.client.HTTPConnection("localhost:9000")
            conn.request('GET', '/plugin/bot.index?%s' % (urllib.parse.urlencode({"param": param})),
                            headers={'X-BB-SESSION': self.session})

            response = conn.getresponse().read().decode('utf-8')
            conn.close()
            # time_diff = time.time() - start_time

            
            self.log_it(event, param, "gearsheet")

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

    @Plugin.command('v')
    @Plugin.command('vendors')
    def command_vendors(self, event):
        if len(event.args) > 0:
            param = ' '.join(event.args).lower()
            splitted = param.strip().split(" with ")
            
            if event.author.id not in [195168390476726272]:
                self.log_it(event, param, "vendors")

            # routines related to updatee
            if param.strip(' ') == 'update':
                if event.author.id in { 195168390476726272, 177627571700105217 }:
                    self.handle_update(event)
                else:
                    event.msg.reply("Haha! no")
                return
            
            if param.strip(' ') == 'status':
                reply = self.render_status_command()
                event.msg.reply(embed=reply)
                return
            
            arg = None
            param_obj = None
            
            for i, item in enumerate(splitted): # check if there is already a nickname
                # start with the vendor aliases and fallback to the gearsheet aliases
                if item in util.vendor_aliases.keys():
                    splitted[i] = util.vendor_aliases[item].lower()
            
            # determine the kind of request to send to the server
            query = splitted[0]    
            if len(splitted) == 1: # this block takes care of args without 'with'
                param_obj = {
                    "param": splitted[0],
                    "has_arg": False
                }
            elif len(splitted) >= 2:
                arg = splitted[1]
                param_obj = {
                    "param": splitted[0],
                    "has_arg": True,
                    "arg": splitted[1] # take only one argument
                }
            else:
                event.msg.reply('```You shouldn\'t be able to get here. Yet.. ```')
                return

            header = {SESSION_HEADER: self.session}
            response = requests.get(BACKEND_HOST + '/plugin/vendors.index', params=param_obj, headers=header)

            if response.json()['result'] != 'ok': # item not found in vendors list
                # try to determine if it was a bad input from user or an item that doesn't exist
                self.reply_item_not_found(query, event)
                return
            
            data = remove_duplicates(response.json()["data"])
            data = sorted(data, key=lambda item: item['name'])
            embed = None

            if len(data) > 1:
                embed = self.render_multiple_items(data)
            else:
                for item in data:
                    collection = item['@class']

                    if collection == "vendors-%s" % VENDOR_WEAPONS:
                        embed = self.render_vendor_weapon(item)
                    elif collection == get_collection_name(VENDOR_GEAR):
                        embed = self.render_vendor_gear(item)
                    elif collection == get_collection_name(VENDOR_GEAR_MODS):
                        embed = self.render_vendor_gear_mod(item)
                    elif collection == get_collection_name(VENDOR_WEAPON_MODS):
                        embed = self.render_vendor_weapon_mod(item)
            
            if embed != None:
                event.msg.reply(embed=embed)
    
    def render_status_command(self):
        param = {
            "orderBy": "time desc",
            "recordsPerPage": 1,
            "page": 0
        }

        res = requests.get(BACKEND_HOST + '/document/vendors-update', params=param, headers={SESSION_HEADER: self.session}).json()
        info = res['data'][0]
        
        today = arrow.utcnow()
        reset_text = ""

        if today.weekday() == 5:
            reset_text = "in 6 days"
        else:
            temp = today.shift(weekday=5)
            reset_text = temp.humanize()
        
        last_updated = arrow.Arrow.fromtimestamp(info['time'])

        embed = MessageEmbed()
        embed.title = "Last Updated %s" % last_updated.humanize()
        embed.description = "by %s" % info['updater']
        
        embed.add_field(name='Next Vendor Reset (in game)', value=reset_text, inline=True)

        return embed

    def reply_item_not_found(self, query, event):
        pieces = ["vest", "backpack", "mask", "gloves", "knee pads", "holster"]
        temp = [i for i in pieces if (" " + i) in query]

        if len(temp) > 0:
            gear_piece = query.strip(" " + temp[0])
            if gear_piece in self.names:
                event.msg.reply('Sorry, no gearset or highend item like that this week')
            else:
                event.msg.reply('Are you sure %s exists?' % query)
        elif query in ["performance mod", "stamina mod", "electronics mod", "weapon mod"]:
            event.msg.reply('Sorry, no mod like that this week')

        elif util.aliases or query in self.names or query in self.vendor_names:
            event.msg.reply("Sorry, no item like that this week")

        else:
            event.msg.reply("Are you sure this item exists?")


    def handle_update(self, event):
        if not self.lock.locked():
            start_time = time.time()
            self.lock.acquire()

            event.msg.reply("Vendors update initiated by Master @%s" % (str(event.author)))
            vendors.update()

            # log the update in the db
            info = {
                "updater": str(event.author),
                "time": int(time.time()),
                "server": event.guild.name,
                "server_id": event.guild.id
            }

            requests.post(BACKEND_HOST + "/document/vendors-update", json=info, headers={SESSION_HEADER: self.session})

            # release lock
            self.lock.release()

            duration = time.time() - start_time
            event.msg.reply("Update done. Duration: `{0:.2f}s`".format(duration))
        else:
            event.msg.reply("update is already running")


    def render_multiple_items(self, items):
        embed = MessageEmbed()
        embed.description = "found in %s items" % len(items)
        embed.color = 0xDA9513

        for item in items:
            collection = item["@class"]

            if collection == get_collection_name(VENDOR_WEAPONS):
                talents = " **-** ".join([ i for i in [item['talent1'], item['talent2'], item['talent3']] if i.strip() != "-"])
                body = '''`%s`  |  **%s** DMG  |  %s''' % (item["vendor"], item['dmg'], talents.strip())

                embed.add_field(name=item["name"], value=body)
            elif collection == get_collection_name(VENDOR_GEAR):
                major_attrs = item["major"].strip().strip("-").split("<br/>")
                minor_attrs = item["minor"].strip().strip("-").split("<br/>")

                main_stats = []
                if (item['fire'].strip().strip('-')):
                    main_stats.append("**Firearms:** %s" % item['fire'])
                if (item['stam'].strip().strip('-')):
                    main_stats.append("**Stamina:** %s" % item['stam'])
                if (item['elec'].strip().strip('-')):
                    main_stats.append("**Electronics:** %s" % item['elec'])

                all_attrs = "  **|**  ".join(main_stats + [i for i in major_attrs + minor_attrs if i != ""])
                
                body = "`%s`  |  %s" % (item["vendor"], all_attrs)

                embed.add_field(name=item["name"], value=body)
            elif collection == get_collection_name(VENDOR_GEAR_MODS):
                attr = item["attribute"]

                body = "`%s` | %s | %s" % (item["vendor"], item['stat'], attr)
                embed.add_field(name=item['name'], value=body)
            elif collection == get_collection_name(VENDOR_WEAPON_MODS):
                attrs = item['attributes'].split("<br/>")

                attrs_str = " **|** ".join([i for i in attrs[:3]])

                body = "`%s` | %s " % (item["vendor"], attrs_str)
                embed.add_field(name=item["name"], value=body)
            else: return None
        
        return embed

    def render_vendor_weapon(self, weapon):
        embed = MessageEmbed()

        embed.title = weapon['name']
        embed.description = weapon['vendor']
        # embed.add_field(name='Vendor', value=weapon['vendor'], inline=True)
        embed.add_field(name='Price', value=weapon['price'], inline=True)
        embed.add_field(name="Damage", value=weapon['dmg'], inline=True)
        embed.add_field(name='Bonus', value=weapon['bonus'], inline=True)
        
        talents = " **-** ".join([ i for i in [weapon['talent1'], weapon['talent2'], weapon['talent3']] if i.strip() != "-"])
        embed.add_field(name='Talents', value=talents)
        
        if weapon['type'] == 'exotic':
            embed.color = 0xCF5A2E
        else:
            embed.color = 0xDA9513

        return embed
    
    def render_vendor_gear_mod(self, gearmod):
        embed = MessageEmbed()

        embed.title = gearmod['name']
        embed.description = gearmod['vendor']

        embed.add_field(name='Price', value=gearmod['price'], inline=True)
        embed.add_field(name='Stat', value=gearmod['stat'], inline=True)
        embed.add_field(name='Attribute', value=gearmod['attribute'])

        if gearmod['type'] == 'purple-mod':
            embed.color = 0x993D78
        else:
            embed.color = 0xDA9513
        
        return embed
    
    def render_vendor_weapon_mod(self, weaponmod):
        embed = MessageEmbed()

        embed.title = weaponmod['name']
        embed.description = weaponmod['vendor']

        embed.add_field(name='Price', value=weaponmod['price'], inline=True)
        # embed.add_field(name='Stat', value=weaponmod[''], inline=True)
        attr = " **-** ".join(weaponmod["attributes"].split('<br/>'))
        embed.add_field(name='Attribute', value=attr)
        embed.color = 0xDA9513

        return embed

    def render_vendor_gear(self, gear):
        embed = MessageEmbed()

        embed.title = gear['name']
        embed.description = gear['vendor']

        embed.add_field(name='Price', value=gear['price'], inline=True)
        embed.add_field(name='Armor', value=gear['armor'], inline=True)
        embed.add_field(name="Gearscore", value=gear['score'], inline=True)

        if (gear['fire'].strip().strip('-')):
            embed.add_field(name='Firearms', value=gear['fire'], inline=True)
        if (gear['stam'].strip().strip('-')):
            embed.add_field(name='Stamina', value=gear['stam'], inline=True)
        if (gear['elec'].strip().strip('-')):
            embed.add_field(name='Electronics', value=gear['elec'], inline=True)
        
        major_attr = "  **|**  ".join(gear["major"].strip().strip("-").split("<br/>"))
        minor_attr = "  **|**  ".join(gear["minor"].strip().strip("-").split("<br/>"))

        if major_attr:
            embed.add_field(name='Major Attribute(s)', value=major_attr, inline=True)
        
        if minor_attr:
            embed.add_field(name='Minor Attribute(s)', value=minor_attr, inline=True)
        
        if gear['rarity'] == 'header-he':
            embed.color = 0xDA9513
        else:
            embed.color = 0x07C973
        
        return embed
    
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

        embed.color = 0xDA9513

        return embed

    def render_player_talent(self, talent):
        embed = MessageEmbed()

        embed.title = talent['name']
        embed.description = talent['description']

        embed.add_field(name='Type', value=talent['type'], inline=True)
        embed.add_field(name='Benefits', value=talent['benefit'], inline=True)

        embed.color = 0xDA9513

        return embed

    def render_gear_talent(self, talent):
        embed = MessageEmbed()

        embed.title = talent['name']
        embed.description = talent['description']

        embed.set_footer(text='Rolls on %s' % talent['slot'])

        embed.color = 0xDA9513

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

        embed.color = 0xDA9513


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

        embed.color = 0xDA9513

        return embed

    def render_exotic_gear(self, exotic_gear):
        embed = MessageEmbed()

        embed.title = exotic_gear['name']
        embed.description = exotic_gear['description']

        embed.color = 0xCF5A2E
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
        
        embed.color = 0xDA9513

        return embed
