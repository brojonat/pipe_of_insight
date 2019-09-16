import sys, os, pdb, json, shutil, time
from io import BytesIO
import urllib.request
import requests


from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from django.utils.text import slugify

from django.conf import settings

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

            apiURLBaseStr = settings.OPENDOTA_API_URL
            imgURLBaseStr = settings.OPENDOTA_IMG_URL
            apiKey = settings.OPENDOTA_API_KEY

            for key, heroData in heroDataDict.items():

                # grab the image from the api
                imgStaticFile = os.path.join(settings.STATIC_ROOT,os.path.basename(heroData['img'])).replace('?','')
                iconStaticFile = os.path.join(settings.STATIC_ROOT,os.path.basename(heroData['icon'])).replace('?','')

                imgQueryStr = '{}{}'.format(imgURLBaseStr,heroData['img'])
                iconQueryStr = '{}{}'.format(imgURLBaseStr,heroData['icon'])

                imgResult = requests.get(imgQueryStr, stream=True)
                iconResult = requests.get(iconQueryStr, stream=True)

                # store the image in static because I want the static resource too
                if imgResult.status_code == 200:
                    with open(imgStaticFile,'wb') as fout:
                        imgResult.raw.decode_content = True 
                        shutil.copyfileobj(imgResult.raw,fout)

                if iconResult.status_code == 200:
                    with open(iconStaticFile,'wb') as fout:
                        iconResult.raw.decode_content = True 
                        shutil.copyfileobj(iconResult.raw,fout)


                # grab the hero instance
                heroInstance = models.Hero.objects.get(name=heroData['localized_name'])
                heroInstance.img.save(
                    os.path.basename(heroData['img']),
                        File(open(imgStaticFile, 'rb'))
                    )
                heroInstance.icon.save(
                    os.path.basename(heroData['icon']),
                        File(open(iconStaticFile, 'rb'))
                    )


                heroInstance.save() 

                # be polite
                time.sleep(1.)

        # catch any/all exceptions
        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to store Hero data: {}'.format(str(e))))

