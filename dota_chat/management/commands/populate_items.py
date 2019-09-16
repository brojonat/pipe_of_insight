import sys, os, pdb, json
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

import dota_chat.models as models

class Command(BaseCommand):
    help = 'Populates items from dotaconstants JSON file'

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
            infile = 'https://raw.githubusercontent.com/brojonat/dotaconstants/master/build/items.json'
        else:
            infile = options.get('infile')

        # grab the hero data
        try:
            # default file on github
            if 'http' in infile:
                response = urllib.request.urlopen(infile)
                itemDataDict = json.loads(response.read())

            # local file option
            else:
                with open(infile,'r') as fin:
                    itemDataDict = json.loads(fin.read())


        # catch bad urls/files
        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to load Item data: {}'.format(str(e))))



        try:

            # populate item models
            skipItemList = ['trident','combo_breaker','super_blink',
                            'pocket_tower']
            for key,itemDict in itemDataDict.items():

                if key not in skipItemList:

                    # grab the desired fields from itemDict
                    defaultsDict = {}
                    keyMap = {  
                                'valveID':'id',
                                'opendota_img':'img',
                                'dname':'dname',
                                'cost':'cost',
                                'notes':'notes',
                                'manaCost':'mc',
                                'cooldown':'cd',
                                'lore':'lore',
                        }

                    for myKey,odKey in keyMap.items():
                        defaultsDict[myKey] = itemDict.get(odKey)

                    if not defaultsDict.get('dname'):
                        defaultsDict['dname'] = slugify(key)

                    # sanity cleaning
                    if not itemDict.get('manaCost'):
                        defaultsDict['manaCost'] = None
                    if not itemDict.get('cooldown'):
                        defaultsDict['cooldown'] = None

                    defaultsDict['slug'] = slugify(key)

                    # model instantiation
                    itemInstance,createdBool = models.Item.objects.get_or_create(
                                                        itemName=key,
                                                        defaults=defaultsDict
                                                    )



        # catch any/all exceptions
        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to store Item data: {}'.format(str(e))))
            pdb.set_trace()
