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
    help = 'Populates ability images from OpenDota urls'

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

            apiURLBaseStr = settings.OPENDOTA_API_URL
            imgURLBaseStr = settings.OPENDOTA_IMG_URL
            apiKey = settings.OPENDOTA_API_KEY

            #items = list(models.Item.objects.filter(opendota_img__is_null=False))
            abilities = list(models.HeroAbility.objects
                                .filter(opendota_img__isnull=False)
                                .exclude(opendota_img__exact='')
                        )

            for ability in abilities:

                try:
                    # grab the image from the api
                    imgStaticFile = os.path.join(settings.STATIC_ROOT,
                                        os.path.basename(ability.opendota_img.split('?')[0]))

                    imgQueryStr = '{}{}'.format(imgURLBaseStr,ability.opendota_img)

                    imgResult = requests.get(imgQueryStr, stream=True)

                    # store the image in static because I want the static resource too
                    if imgResult.status_code == 200:
                        with open(imgStaticFile,'wb') as fout:
                            imgResult.raw.decode_content = True 
                            shutil.copyfileobj(imgResult.raw,fout)

                    # grab the hero instance
                    ability.img.save(
                        os.path.basename(ability.opendota_img.split('?')[0]),
                            File(open(imgStaticFile, 'rb'))
                        )
                    ability.save() 

                    # be polite
                    time.sleep(0.5)

                # catch any/all exceptions
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR('Failed to store Ability data: {}'.format(str(e))))
                    #pdb.set_trace()


