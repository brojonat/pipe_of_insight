import sys, os, pdb, json, shutil, time

import numpy as np 

from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA

from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from django.utils.text import slugify

from django.conf import settings

import dota_chat.models as models
import dota_chat.custom_sentiment_analyzers as custom_analyzers


class Command(BaseCommand):
    help = 'Populates hero models from dotaconstants JSON file'

    def add_arguments(self, parser):
        # required args
        parser.add_argument('--verbose', action='store_true')
        # Named (optional) arguments
        # parser.add_argument(
        #     '--delete',
        #     action='store_true',
        #     help='Delete poll instead of closing it',
        # )
        pass

    def handle(self, *args, **options):

        try:
            # init
            count = 0
            allHeros = models.Hero.objects.all()
            heroCount = allHeros.count()

            # for each hero
            for hero in allHeros:
                count += 1
                outStr = 'Working on hero {} ({} / {}) '.format(hero.prettyName,count,heroCount)
                self.stdout.write(self.style.WARNING(outStr))

                metaHeroGames = models.Player.objects.filter(
                                        hero=hero,
                    ).count()
                metaHeroWins = models.Player.objects.filter(
                                        hero=hero,
                                        wonMatch__exact=True
                    ).count()
                metaHeroWinRate = 1.*metaHeroWins / (1.*metaHeroGames)

                hero.metaWinRate = metaHeroWinRate
                hero.save()

        # catch any/all exceptions
        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to store Hero meta winrate: {}'.format(e)))

