import sys, os, pdb, time, datetime

import urllib.request
import requests
import boto3

import numpy as np 
import pandas as pd 

from django.db.models import F
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import dota_chat.models as models
import dota_chat.constants as dc_constants

def getHeroStats(account_id):
    apiURLBaseStr = settings.OPENDOTA_API_URL
    apiKey = settings.OPENDOTA_API_KEY
    queryStr = '/'.join([apiURLBaseStr,'players',str(account_id),'heroes'])
    params = {
        'api_key': apiKey,
    }
    queryRes = requests.get(queryStr,params=params)

    if queryRes.status_code == 200:
        return queryRes.json()
    else:
        return []



class Command(BaseCommand):
    help = 'Populates Player slug fields'

    def add_arguments(self, parser):
        # required args
        # Named (optional) arguments
        parser.add_argument(
            '--date-min',
            help='YYYY-MM-DD max matches to look thru',
        )
        parser.add_argument(
            '--date-max',
            help='YYYY-MM-DD max matches to look thru',
        )
        pass

    def handle(self, *args, **options):

        # init
        ANON_ID = 4294967295

        date_min = options.get('date_min')
        date_max = options.get('date_max')

        # grab users from a specific day
        if date_min and date_max:
            start_query = datetime.datetime.strptime(date_min,'%Y-%m-%d').timestamp()
            end_query = datetime.datetime.strptime(date_max,'%Y-%m-%d').timestamp()
            allUserQS = models.Match.objects.values('player__valveID__valveID')
            allUserQS = allUserQS.filter(
                                start_time__gte=start_query, 
                                start_time__lte=end_query
                            )
            allUserQS = allUserQS.distinct()

        # grab all users
        else:
            warnStr = 'For now, it\'s requried that you supply a date range'
            self.stdout.write(self.style.SUCCESS(warnStr))
            sys.exit(1)

        # for each user, pull their stats
        lastAPICall = 0.
        userIDKey = 'player__valveID__valveID'
        for user in allUserQS.iterator():
            try:
                userInstance = models.SteamUser.objects.get(id=user[userIDKey])
                isValidUser = user[userIDKey] != ANON_ID
                needsHeroStatData = not models.UserHeroStats.objects.filter(
                                            user=userInstance).exists()

                if isValidUser and needsHeroStatData:

                    # rate limit
                    while time.now() - lastAPICall < 0.05:
                        time.sleep(0.02)

                    statsList = getHeroStats(userInstance.valveID)
                    lastAPICall = time.now()

                    for heroStatDict in statsList:
                        # unpack
                        statHero = models.Hero.objects.get(valveID=int(heroStatDict['hero_id']))
                        playerNGames = heroStatDict['games']
                        playerNGames_with = heroStatDict['with_games']
                        playerNGames_against = heroStatDict['against_games']
                        playerWinGames = heroStatDict['win']
                        playerWinGames_with = heroStatDict['with_win']
                        playerWinGames_against = heroStatDict['against_win']

                        # defaults
                        hsDefaultDict = {
                                'games': playerNGames,
                                'win': playerWinGames,
                                'with_games': playerNGames_with,
                                'with_win': playerWinGames_with,
                                'against_games': playerNGames_against,
                                'against_win': playerWinGames_against,
                            }
                        # store
                        hsInstance,hsCreated = models.UserHeroStats.objects.get_or_create(
                                                        user=userInstance,
                                                        hero=statHero,
                                                        defaults=hsDefaultDict
                                                    )



                successStr = 'Successfully logged user stats {}'.format(userInstance)
                self.stdout.write(self.style.SUCCESS(successStr))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR('Failed to log user stats {}: {}'.format(userInstance,str(e))))

