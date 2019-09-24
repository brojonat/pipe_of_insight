import sys, os, pdb, shutil, time, json, io, ast, copy, traceback
import urllib.request
import requests
import boto3


import numpy as np 
import pandas as pd 

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import dota_chat.models as models
import dota_chat.constants as dc_constants

def str2bool(inStr):
    ''' Returns True/False based on some heuristics '''

    if isinstance(inStr,bool):
        return inStr
    else:
        isEmpty = inStr == ''
        isNull = inStr is None
        falseSignal = 'f' in inStr.lower()

        if isEmpty or isNull or falseSignal:
            return False
        else:
            return True

def slot2team(slot):
    ''' Quick conversion from player_slot to team '''
    if slot < 5:
        return 'RADIANT'
    else:
        return 'DIRE'

def getHeroStats(account_id):
    apiURLBaseStr = settings.OPENDOTA_API_URL
    apiKey = settings.OPENDOTA_API_KEY
    queryStr = '/'.join([apiURLBaseStr,'players',str(account_id),'heroes'])
    params = {
        'api_key': apiKey,
    }
    queryRes = requests.get(queryStr,params=params)
    time.sleep(0.02)

    if queryRes.status_code == 200:
        return queryRes.json()
    else:
        return []


def ParseChat(data):
    ''' Returns a list of chat entries (list of dicts) '''
    chatData = []

    try:
        if data is not np.nan and data != '':
            # convert OpenDota form to a set
            # this is apparently necessary because nested quotes 
            # are not getting parsed correctly
            dataSet = ast.literal_eval(data)

            # parse each item in the set
            for item in dataSet:
                chatEntry = json.loads(item)
                chatData.append(chatEntry)

    except Exception as e:
        errStr = 'CAUGHT EXCEPTION: {}'.format(e)
        print(errStr)
        chatData = []

    return chatData

def ParsePGroup(data):
    ''' Returns a dict of pgroup information (dict) '''
    try:
        retData = json.loads(data)
    except Exception as e:
        errStr = 'CAUGHT EXCEPTION: {}'.format(e)
        print(errStr)
        retData = {}
    return retData

def parse_chat_pgroup(chatList,playerList,num_humans=10,QUERY_OPENDOTA_API=False,RADIANT_WIN=False):
    ''' Merges chat and player info into a dict '''

    # init
    retDict = {}
    ANON_CODE = 4294967295
    ANON_COUNT = 0

    # loop over each player, extract info
    for playerInfo in playerList:

        # this is some weird condition where the hero and player are unknown
        if playerInfo['hero_id'] != 0 and playerInfo.get('account_id') is not None:

            # init
            restructuredInfo = copy.deepcopy(playerInfo)
            playerID = restructuredInfo.get('account_id')

            # mock up SteamID if EXPOSE MATCH DATA TO PUBLIC not enabled
            if playerID == ANON_CODE:
                ANON_COUNT += 1
                playerName = 'ANON_{}_4294967295'.format(ANON_COUNT)

            # check to see if we have this user
            elif models.SteamUser.objects.filter(valveID=playerID).exists():
                playerName = models.SteamUser.objects.get(valveID=playerID).name

            # otherwise ping the OpenDota API for the username
            elif QUERY_OPENDOTA_API:
                apiURLBaseStr = settings.OPENDOTA_API_URL
                apiKey = settings.OPENDOTA_API_KEY
                queryStr = '{}/players/{}?api_key={}'.format(apiURLBaseStr,playerID,apiKey)
                queryRes = requests.get(queryStr)
                time.sleep(0.05) # will prevent rate exceeding

                playerName = None
                if queryRes.status_code == 200:
                    try:
                        queryJSON = queryRes.json()
                        playerName = queryJSON.get('profile').get('personaname')
                    except Exception as e:
                        playerName = 'BAD_PROFILE_RESULT_{}'.format(playerID)

                # catch all failures on playerName
                if not playerName:
                    playerName = 'STATUS_NOT_200_{}'.format(playerID)
            else:
                playerName = 'STEAMID_{}'.format(playerID)

            restructuredInfo['playerName'] = playerName
            restructuredInfo['chat'] = []

            # map the chat items to users using player_slot
            if chatList != [] and chatList is not None:
                for chatEntry in chatList:
                    chatSlot = chatEntry.get('slot')

                    chatSlotNotNone = (chatSlot is not None)
                    chatSlotIsPlayer = (chatSlot == restructuredInfo['player_slot'])
                    chatNotChatwheel = (chatEntry.get('type') != 'chatwheel')
                    if chatSlotNotNone and chatSlotIsPlayer and chatNotChatwheel:
                        # construct entry for storage
                        chatEventTuple = (chatEntry['time'],chatEntry['key'])
                        restructuredInfo['chat'].append(chatEventTuple)

                        # pop that element so the loop isn't as obnoxious
                        chatList.remove(chatEntry)

            # determine if victory or not victory
            team = slot2team(restructuredInfo['player_slot'])
            wonOnRadiant = (team == 'RADIANT' and RADIANT_WIN)
            wonOnDire = (team == 'DIRE' and not RADIANT_WIN)
            if wonOnRadiant or wonOnDire:
                wonMatch = True
            else:
                wonMatch = False

            restructuredInfo['team'] = team
            restructuredInfo['wonMatch'] = wonMatch


            # store info in a new dict keyed on account_id
            if playerID:
                retDict[playerID] = restructuredInfo

    return retDict



class Command(BaseCommand):
    help = 'Populates hero models from dotaconstants JSON file'

    def add_arguments(self, parser):
        # required args
        parser.add_argument('--bucket-key-file',
                    help='file of match IDs on S3 (e.g. dota2/match_dump_2019-09-01.txt')
        parser.add_argument('--verbose', action='store_true')
        parser.add_argument('--query', action='store_true')
        parser.add_argument('--query-for-user-hero-stats',action='store_true')

        # Named (optional) arguments
        # parser.add_argument(
        #     '--delete',
        #     action='store_true',
        #     help='Delete poll instead of closing it',
        # )
        pass

    def handle(self, *args, **options):

        # init
        bucket = 'brojonat.dota2'
        bucketKeyFile = options.get('bucket_key_file')


        VERBOSE = options.get('verbose')
        QUERY = options.get('query')
        QUERY_FOR_USER_HERO_STATS = options.get('query_for_user_hero_stats')

        ANON_ID = 4294967295
        matchCount = 0

        try:

            s3Client = boto3.client('s3')
            s3Obj = s3Client.get_object(Bucket=bucket, Key=bucketKeyFile)
            df = pd.read_csv(
                        io.BytesIO(s3Obj['Body'].read()),
                        header=None,
                        names=['matchIDs']
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to retrieve file from S3: {}'.format(str(e))))
            sys.exit(1)

        matchList = df['matchIDs'].tolist()
        nMatches = len(matchList)

        # loop over the file iterator
        for matchID in matchList:

            try:

                matchCount += 1


                apiURLBaseStr = settings.OPENDOTA_API_URL
                apiKey = settings.OPENDOTA_API_KEY

                url = '{}/matches/{}'.format(apiURLBaseStr,matchID)
                params = {
                    'api_key':apiKey
                }
                
                queryRes = requests.get(url,params=params)
                time.sleep(0.05) # will prevent rate exceeding

                match = queryRes.json()

                if VERBOSE:
                    outStr = 'Working on match {} '.format(matchID)
                    outStr += '({} of {})'.format(matchCount,nMatches)
                    self.stdout.write(self.style.SUCCESS(outStr))

                # init
                matchDict = {}

                # extract/combine/merge
                radiantWinBool = str2bool(match['radiant_win'])

                ### need to rewrite this function ###
                playerEntries = parse_chat_pgroup(
                                    match['chat'],match['players'],
                                    num_humans=match['human_players'],
                                    QUERY_OPENDOTA_API=QUERY,
                                    RADIANT_WIN=radiantWinBool
                    )

                # get the canned quantities
                matchDict['match_id'] = match.get('match_id')
                matchDict['match_seq_num'] = match.get('match_seq_num')
                matchDict['start_time'] = match.get('start_time')
                matchDict['game_mode'] = match.get('game_mode')
                matchDict['region'] = match.get('region')
                matchDict['cluster'] = match.get('cluster')
                matchDict['patch'] = match.get('patch')
                matchDict['picks_bans'] = match.get('picks_bans')
                matchDict['duration'] = match.get('duration')
                matchDict['human_players'] = match.get('human_players')
                matchDict['radiant_win'] = radiantWinBool

                # match
                bannedKeys = ['match_id','picks_bans']
                matchDefaults = {key:val for key,val in matchDict.items() if key not in bannedKeys}
                matchInstance,matchCreated = models.Match.objects.get_or_create(
                                                        matchID=matchDict['match_id'],
                                                        defaults=matchDefaults
                    )

                # populate bans
                if matchDict['picks_bans'] is not None:
                    for item in matchDict['picks_bans']:
                        if not item['is_pick']:
                            heroInstance = models.Hero.objects.get(valveID=item['hero_id'])
                            matchInstance.bans.add(heroInstance)
                            if VERBOSE:
                                outStr = 'Banned {}'.format(heroInstance)
                                self.stdout.write(
                                    self.style.WARNING(
                                        outStr
                                    )
                                )

                # for each player in the match
                for userID,playerEntry in playerEntries.items():

                        # hero
                        heroInstance = models.Hero.objects.get(
                                            valveID=playerEntry['hero_id']
                            )

                        # user
                        if playerEntry['account_id'] == ANON_ID:
                            userDefaults = {'name': 'ANONYMOUS'}
                        else:
                            userDefaults = {'name': playerEntry['playerName']}
                        userInstance,userCreated = models.SteamUser.objects.get_or_create(
                                                        valveID=playerEntry['account_id'],
                                                        defaults=userDefaults
                            )

                        # create Player
                        playerDefaults = {
                                'name':playerEntry['playerName'], # i don't want to update name at this time
                                'team':playerEntry['team'],
                                'wonMatch':playerEntry['wonMatch']
                            }
                        playerInstance, playerCreated = models.Player.objects.update_or_create(
                                                                valveID=userInstance,
                                                                hero=heroInstance,
                                                                matchID=matchInstance,
                                                                defaults=playerDefaults
                            )

                        isValidUser = userInstance.valveID != ANON_ID
                        needsHeroStatData = not models.UserHeroStats.objects.filter(
                                                        user=userInstance,
                                                        hero=heroInstance).exists() # not exact but close
                        if QUERY_FOR_USER_HERO_STATS and isValidUser and needsHeroStatData:
                            statsList = getHeroStats(userInstance.valveID)
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

                        # finally, chat entry
                        for chat in playerEntry['chat']:
                            chatTime = chat[0]
                            chatText = chat[1]
                            chatEntry, chatCreated = models.ChatEntry.objects.get_or_create(
                                                            player=playerInstance,
                                                            chatTime=chatTime,
                                                            chatText=chatText
                                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        'Failed to add match: {}'.format(
                            str(traceback.format_exc())
                        )
                    )
                )