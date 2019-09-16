import sys, os, pdb, json
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

import dota_chat.models as models

class Command(BaseCommand):
    help = 'Populates hero models from dotaconstants JSON file'

    def add_arguments(self, parser):
        # required args
        parser.add_argument('--verbose', action='store_true')
        parser.add_argument('--infile',nargs='+')
        # Named (optional) arguments
        # parser.add_argument(
        #     '--delete',
        #     action='store_true',
        #     help='Delete poll instead of closing it',
        # )
        pass

    def handle(self, *args, **options):

        if not options.get('infile'):
            infile = 'https://raw.githubusercontent.com/brojonat/dotaconstants/master/build/heroes.json'
        else:
            infile = options.get('infile')

        # grab the hero data
        try:
            # default file on github
            if 'http' in infile:
                response = urllib.request.urlopen(infile)
                heroDataDict = json.loads(response.read())

            # local file option
            else:
                with open(infile,'r') as fin:
                    heroDataDict = json.loads(fin.read())

        # catch bad urls/files
        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to load Hero data: {}'.format(str(e))))

        # load it into model instances
        try:
            for key, heroData in heroDataDict.items():
                # some basic transforms to maintain sanity
                # dunno why some heros have null instead of 0
                if heroData['base_health_regen'] is None:
                    heroData['base_health_regen'] = 0
                # load the basic hero data
                heroInstance,createdBool = models.Hero.objects.get_or_create(
                                                    name=heroData['localized_name'],
                                                    defaults={ 'slug': slugify(heroData['localized_name']),
                                                               'valveID': heroData['id'],
                                                               'valveName': heroData['name'],
                                                               'primary_attr': heroData['primary_attr'],
                                                               'attack_type': heroData['attack_type'],
                                                               'opendota_img': heroData['img'],
                                                               'opendota_icon': heroData['icon'],
                                                               'base_health': heroData['base_health'],
                                                               'base_health_regen': heroData['base_health_regen'],
                                                               'base_mana': heroData['base_mana'],
                                                               'base_mana_regen': heroData['base_mana_regen'],
                                                               'base_armor': heroData['base_armor'],
                                                               'base_mr': heroData['base_mr'],
                                                               'base_attack_min': heroData['base_attack_min'],
                                                               'base_attack_max': heroData['base_attack_max'],
                                                               'base_str': heroData['base_str'],
                                                               'base_agi': heroData['base_agi'],
                                                               'base_int': heroData['base_int'],
                                                               'str_gain': heroData['str_gain'],
                                                               'agi_gain': heroData['agi_gain'],
                                                               'int_gain': heroData['int_gain'],
                                                               'attack_range': heroData['attack_range'],
                                                               'projectile_speed': heroData['projectile_speed'],
                                                               'attack_rate': heroData['attack_rate'],
                                                               'move_speed': heroData['move_speed'],
                                                               'turn_rate': heroData['turn_rate'],
                                                               'cm_enabled': heroData['cm_enabled'],
                                                               'legs': heroData['legs']
                                                        },
                                                )
                # add the many to many field
                for role in heroData['roles']:
                    roleInstance = models.HeroRoles.objects.get(role=role)
                    heroInstance.roles.add(roleInstance)
                # must save for M2M adds, could listen for signals...
                heroInstance.save() 

        # catch any/all exceptions
        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to store Hero data: {}'.format(str(e))))
            pdb.set_trace()

