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

            analyzer = custom_analyzers.DefaultCustomAnalyzer()
            analyzer.update_hardcoded_dota_sentiments()

            # for each hero
            for hero in allHeros:
                count += 1
                outStr = 'Working on hero {} ({} / {}) '.format(hero.prettyName,count,heroCount)
                self.stdout.write(self.style.WARNING(outStr))

                # retrieve the chat entries for all players on this hero
                allChat = models.Player.objects.values('matchID__matchID','chatentry__chatText')
                allChat = allChat.filter(hero=hero)

                # unpack and store in a bag
                wordBagDict = {}
                for item in allChat:
                    matchID = item['matchID__matchID']
                    chatText = item['chatentry__chatText']
                    if chatText is not None:
                        if matchID not in wordBagDict:
                            wordBagDict[matchID] = [chatText]
                        else:
                            wordBagDict[matchID].append(chatText)

                # loop over match,wordBag and compute the average sentiment per game
                gameSentimentList = []

                for matchID,wordBag in wordBagDict.items():
                    
                    # compute sentiment
                    wordBagStr = ''
                    for sentence in wordBag:
                        wordBagStr += '\n {}'.format(sentence)
                    sentScoreDict = analyzer.polarity_scores(wordBagStr)

                    # store compound sentiment
                    gameSentimentList.append(sentScoreDict['compound'])

                # average, store in model, save
                averageSentiment = np.array(gameSentimentList).mean()
                hero.chatSentiment = averageSentiment
                hero.save()

        # catch any/all exceptions
        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to store Hero sentiment: {}'.format(e)))

