import sys, os, pdb, shutil, time, json, io, ast, copy, traceback
import urllib.request
import requests
import boto3


import numpy as np 
import pandas as pd 

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import dota_chat.models as models

def str2bool(inStr):
    ''' Returns True/False based on some heuristics '''
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

def parse_chat_pgroup(chatList,playerDict,num_humans=10,QUERY_OPENDOTA_API=False,RADIANT_WIN=False):
    ''' Merges chat and player info into a dict '''

    # init
    retDict = {}
    ANON_CODE = 4294967295
    ANON_COUNT = 0

    # loop over each player, extract info
    for key,playerInfo in playerDict.items():

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
            if chatList != []:
                for chatEntry in chatList:
                    if chatEntry.get('slot') == restructuredInfo['player_slot']:

                        # construct entry for storage
                        chatEventTuple = (chatEntry['time'],chatEntry['key'])
                        restructuredInfo['chat'].append(chatEventTuple)

                        # pop that element so the loop isn't as obnoxious
                        chatList.remove(chatEntry)
                    elif chatEntry.get('slot') is None:
                        # self.stdout.write(
                        #     self.style.WARNING(
                        #         'What is going on here: {}'.format(chatEntry)
                        #     )
                        # )
                        print('No key \'slot\' for chatEntry: {}'.format(chatEntry))

                    else:
                        pass

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
    help = '\nNOTE: THIS IS DEPRICATED!!!!!!!\n'
    help += 'Populates hero models from dotaconstants JSON file\n'
    help += 'IMPORTANT: since this is using the ORM bulk_create,\n'
    help += 'protections like referential integrity may be disabled!\n'
    help += 'This should only be used on a clean/empty DB'

    def add_arguments(self, parser):
        # required args
        parser.add_argument('--verbose', action='store_true')
        parser.add_argument('--query', action='store_true')
        parser.add_argument('--bulk', action='store_true')


        # Named (optional) arguments
        # parser.add_argument(
        #     '--delete',
        #     action='store_true',
        #     help='Delete poll instead of closing it',
        # )
        pass

    def handle(self, *args, **options):

        # init
        VERBOSE = options.get('verbose')
        QUERY = options.get('query')
        ANON_ID = 4294967295
        bucket = 'brojonat.dota2'
        bucketKey = 'dota2/matches_small.csv'
        matchCount = 0

        if not options.get('bulk'):
            self.stdout.write(
                self.style.ERROR('For safety, you need to set the --bulk flag. Exiting.'))
            sys.exit(1)

        try:

            s3Client = boto3.client('s3')
            s3Obj = s3Client.get_object(Bucket=bucket, Key=bucketKey)
            df_chunk_reader = pd.read_csv(
                                    io.BytesIO(s3Obj['Body'].read()),
                                    converters={'chat':ParseChat,'pgroup':ParsePGroup},
                                    chunksize=1024
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to connect to S3 bucket: {}'.format(str(e))))
            sys.exit(1)

        try:

            # loop over the file iterator
            for chunk in df_chunk_reader:
                # for BULK: refresh/init all batch create lists here
                playerListBulkCreate = []
                chatListBulkCreate = []
                chatIndex = 0
                playerIndex = 0
                chatPlayerMap = {} # chatPlayerMap[chatIndex] = playerIndex

                # loop over the dataframe rows
                for index, match in chunk.iterrows():
                    matchCount += 1

                    if VERBOSE:
                        outStr = 'Working on match {} ({} of ?)'.format(match.match_id,matchCount)
                        self.stdout.write(self.style.SUCCESS(outStr))


                    # init
                    matchDict = {}

                    # extract/combine/merge
                    radiantWinBool = str2bool(match.radiant_win)
                    playerEntries = parse_chat_pgroup(match.chat,match.pgroup,
                                                        num_humans=match.human_players,
                                                        QUERY_OPENDOTA_API=QUERY,
                                                        RADIANT_WIN=radiantWinBool
                                        )

                    # get the canned quantities
                    matchDict['match_id'] = match.match_id
                    matchDict['match_seq_num'] = match.match_seq_num
                    matchDict['start_time'] = match.start_time
                    matchDict['duration'] = match.duration
                    matchDict['human_players'] = match.human_players

                    # computed quantities
                    matchDict['radiant_win'] = radiantWinBool
                    matchDict['player_entries'] = playerEntries

                    matchDefaults = {
                        'match_seq_num': matchDict['match_seq_num'],
                        'start_time': matchDict['start_time'],
                        'duration': matchDict['duration'],
                        'human_players': matchDict['human_players']
                    }

                    # match
                    matchInstance,matchCreated = models.Match.objects.get_or_create(
                                                            matchID=matchDict['match_id'],
                                                            defaults=matchDefaults
                        )

                    # for each player in the match
                    for userID,playerEntry in matchDict['player_entries'].items():

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
                                'name':playerEntry['playerName'],
                                'team':playerEntry['team'],
                                'wonMatch':playerEntry['wonMatch']
                            }
                        playerInstance = models.Player(
                                            valveID=userInstance,
                                            hero=heroInstance,
                                            matchID=matchInstance,
                                            **playerDefaults
                            )
                        playerListBulkCreate.append(playerInstance)

                        # finally, chat entry
                        for chat in playerEntry['chat']:
                            chatTime = chat[0]
                            chatText = chat[1]
                            chatInstance = models.ChatEntry(
                                                    player=playerInstance,
                                                    chatTime=chatTime,
                                                    chatText=chatText
                                )
                            chatListBulkCreate.append(chatInstance)

                            chatPlayerMap[chatIndex] = playerIndex
                            chatIndex += 1 #increment after every chat

                        playerIndex += 1 # increment after every player


                # bulk_create the Players
                newPlayersBulk = models.Player.objects.bulk_create(playerListBulkCreate)

                # fortunately with Postgres we can access the new PKs after bulk_create
                # so now all the hard work pays off: we can loop over chats and simply
                # look up who the player was for that chatIndex in chatPlayerMap,
                # then we can assign the Player instance to each chat foreign key,
                # rather than having to do a lookup in the DB

                chatIndex = 0 # reinitialize
                for chatEntry in chatListBulkCreate:
                    newPlayerInstance = newPlayersBulk[chatPlayerMap[chatIndex]]
                    chatEntry.player = newPlayerInstance
                    chatIndex += 1 # increment after every chat

                # now store the chats
                models.ChatEntry.objects.bulk_create(chatListBulkCreate)



        except Exception as e:

            self.stdout.write(
                self.style.ERROR(
                    'Failed to add match: {}'.format(
                        str(traceback.format_exc())
                    )
                )
            )

            pdb.set_trace()
