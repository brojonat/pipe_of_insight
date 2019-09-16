import sys, os, pdb, json
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

import dota_chat.models as models

class Command(BaseCommand):
    help = 'Populates abilities from dotaconstants JSON file'

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
            infile = 'https://raw.githubusercontent.com/brojonat/dotaconstants/master/build/abilities.json'
        else:
            infile = options.get('infile')

        # grab the hero data
        try:
            # default file on github
            if 'http' in infile:
                response = urllib.request.urlopen(infile)
                abilityDataDict = json.loads(response.read())

            # local file option
            else:
                with open(infile,'r') as fin:
                    abilityDataDict = json.loads(fin.read())


        # catch bad urls/files
        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to load Ability data: {}'.format(str(e))))



        try:

            abilitySkipList = ['dota_base_ability']
            # populate ability models
            for key,abilityDict in abilityDataDict.items():

                if key not in abilitySkipList:

                    if abilityDict.get('dname') is not None:

                        # grab the desired fields from abilityDict
                        defaultsDict = {}
                        keyMap = {  'dname':'dname',
                                    'dmg_type':'dmg_type',
                                    'bkbPierce':'bkbpierce',
                                    'description':'desc',
                                    'opendota_img':'img',
                                    'manaCost':'mc',
                                    'cooldown':'cd'
                            }
                        blankSet = {'dmg_type'}

                        for myKey,odKey in keyMap.items():
                            defaultsDict[myKey] = abilityDict.get(odKey)

                            # we implement strings null=False, blank=True
                            # so enforce that here
                            if myKey in blankSet and abilityDict.get(odKey) is None:
                                defaultsDict[myKey] = ''

                        # sanity cleaning
                        # bkbPierce to boolean
                        if not abilityDict.get('bkbpierce') or abilityDict.get('bkbpierce') == 'No':
                            defaultsDict['bkbPierce'] = False
                        else:
                            defaultsDict['bkbPierce'] = True

                        # manaCost and cooldown to lists when single value
                        if defaultsDict.get('manaCost'):
                            if isinstance(defaultsDict.get('manaCost'),str):
                                defaultsDict['manaCost'] = [float(defaultsDict['manaCost'])]
                        if defaultsDict.get('cooldown'):
                            if isinstance(defaultsDict.get('cooldown'),str):
                                defaultsDict['cooldown'] = [float(defaultsDict['cooldown'])]


                        # model instantiation
                        abilityInstance,createdBool = models.HeroAbility.objects.get_or_create(
                                                            abilityName=key,
                                                            defaults=defaultsDict
                                                        )

                        # add many to many fields

                        # sometimes behavior is a string, not a list, and also can have null
                        if abilityDict.get('behavior'):
                            if isinstance(abilityDict['behavior'],list):
                                behaviors = abilityDict['behavior']
                            else:
                                behaviors = [abilityDict['behavior']]

                        for behavior in behaviors:
                            if behavior is not None:
                                behaviorInstance = models.AbilityBehaviors.objects.get(behavior=behavior)
                                abilityInstance.behavior.add(behaviorInstance)
                        abilityInstance.save() 

                    else:
                        abilityInstance,createdBool = models.HeroAbility.objects.get_or_create(
                                                        abilityName=key,
                                                        defaults={
                                                            'dmg_type': 'null', # DO NOT DO THIS
                                                            'dname': key,
                                                        }
                            )
                        hiddenBehavior = models.AbilityBehaviors.objects.get(behavior='Hidden')
                        abilityInstance.behavior.add(hiddenBehavior)
                        abilityInstance.save()



        # catch any/all exceptions
        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to store Ability data: {}'.format(str(e))))
            pdb.set_trace()
