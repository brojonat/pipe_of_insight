import os, sys, pdb, shutil, datetime
import json, io, ast, copy, time, argparse, pickle
from collections import OrderedDict 
import requests
import numpy as np 
import pandas as pd 

import scipy as sp
from scipy import signal
from scipy import signal
from scipy.special import expit

from sklearn.linear_model import LogisticRegression
from sklearn import metrics as metrics
from sklearn.model_selection import train_test_split,GridSearchCV

import xgboost as xgb

from matplotlib import pyplot as plt
import seaborn as sns # after mpl

import boto3

import django
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

# import the django models
from dota_chat import models


def getHeroStats(account_id):
    ''' Retrieve player/hero stats from OpenDota '''

    apiURLBaseStr = settings.OPENDOTA_API_URL
    apiKey = settings.OPENDOTA_API_KEY
    queryStr = '/'.join([apiURLBaseStr,'players',str(account_id),'heroes'])
    params = {
        'api_key': apiKey,
    }
    queryRes = requests.get(queryStr,params=params)

    if queryRes.status_code == 200:
        return queryRes.json()
    elif queryRes.status_code == 429:
        print('OOPS, RATE LIMIT EXCEEDED')
        time.sleep(0.05)
        return getHeroStats(account_id)
    else:
        return []

def calculate_features(game,feature_list=[],QUERY_OPEN_DOTA=False,SKIP_PLAYER_STATS=False):
    ''' Calculate relative features from draft data '''

    radiant_features = {key: 0 for key in feature_list}
    dire_features = {key: 0 for key in feature_list}
    featureDict = {
            'RADIANT':radiant_features,
            'DIRE':dire_features
        }

    # target variable
    featureDict['RADIANT']['win'] = game.radiant_win
    featureDict['DIRE']['win'] = not game.radiant_win

    featureDict['RADIANT']['matchID'] = game.matchID
    featureDict['DIRE']['matchID'] = game.matchID

    # add chat sentiment
    if 'chat_sentiment' in feature_list:
        featureDict['RADIANT']['chat_sentiment'] = []
        featureDict['DIRE']['chat_sentiment'] = []

    allHeroRoles = models.HeroRoles.objects.all()

    for side in ['RADIANT','DIRE']:

        players = models.Player.objects.filter(
                        matchID=game,
                        team__iexact=side
                    )

        team_n_public = 0
        meta_winrate_hero_list = []

        player_ngames_hero_list = []
        player_ngames_with_hero_list = []
        player_ngames_against_hero_list = []

        player_winrate_hero_list = []
        player_winrate_with_hero_list = []
        player_winrate_against_hero_list = []

        for player in players:

            account_id = player.valveID.valveID
            hero = player.hero 
            roles = hero.roles.all()
            abilities = hero.abilities.all()

            # get the meta win rate for the hero
            teamAverageMetaBool = ('team_average_meta_win_rate' in feature_list)
            teamTopMetaBool = ('team_top_meta_win_rate' in feature_list)
            if teamAverageMetaBool or teamTopMetaBool:
                metaHeroGames = models.Player.objects.filter(
                                        hero=hero,
                    ).count()
                metaHeroWins = models.Player.objects.filter(
                                        hero=hero,
                                        wonMatch__exact=True
                    ).count()
                metaHeroWinRate = 1.*metaHeroWins / (1.*metaHeroGames)
                meta_winrate_hero_list.append(metaHeroWinRate)

            # assemble behavior list for this hero
            behaviorList = []
            for ability in abilities:
                for behavior in ability.behavior.all():
                    behaviorList.append(behavior.behavior.lower().replace(' ','_'))

            # first capture role and ability behavior features
            for feature in feature_list:

                # loop over roles, add role-based features
                for role in roles:
                    if '_'.join(feature.split('_')[1:]).lower() == role.role.lower():
                        try:
                            featureDict[side][feature] += 1
                        except KeyError:
                            print('Key {} not in featureDict'.format(feature))

                # now loop over abilities, add ability-based features
                for behavior in behaviorList:
                    if '_'.join(feature.split('_')[1:]).lower() == behavior.lower():
                        featureDict[side][feature] += 1

            # add chat sentiment
            if 'chat_sentiment' in feature_list:
                featureDict[side]['chat_sentiment'].append(hero.chatSentiment)

            # now add player-based features
            ## 1. retrieve player rank and ngames with hero
            if account_id != settings.NULL_ACCOUNT_ID and not SKIP_PLAYER_STATS:
                team_n_public += 1

                userInstance = models.SteamUser.objects.get(valveID=account_id)

                # check if the user has stats in our DB
                if models.UserHeroStats.objects.filter(user=userInstance).exists():
                    print('FOUND USER {} IN THE DATABSE!'.format(userInstance.valveID))
                    heroStats = models.UserHeroStats.objects.get(user=userInstance,hero=hero)
                    heroStatsList = [{
                            'hero_id': hero.valveID,
                            'games': heroStats.games,
                            'win': heroStats.win,
                            'with_games': heroStats.with_games,
                            'with_win': heroStats.with_win,
                            'against_games': heroStats.against_games,
                            'against_win': heroStats.against_win,
                        }]

                # if not, query from OpenDota and store all the player's stats
                elif QUERY_OPEN_DOTA:

                    print('QUERYING OD FOR PLAYER STATS')

                    statsList = getHeroStats(userInstance.valveID)
                    userStatBulkCreateList = []

                    for heroStatDict in statsList:
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
                        hsInstance = models.UserHeroStats(
                                        user = userInstance,
                                        hero = statHero,
                                        games = playerNGames,
                                        win = playerWinGames,
                                        with_games = playerNGames_with,
                                        with_win = playerWinGames_with,
                                        against_games = playerNGames_against,
                                        against_win = playerWinGames_against
                            )
                        userStatBulkCreateList.append(hsInstance)

                    try:
                        models.UserHeroStats.objects.bulk_create(userStatBulkCreateList)
                    except IntegrityError:
                        for obj in userStatBulkCreateList:
                            try:
                                obj.save()
                            except IntegrityError:
                                continue

                    # now store the hero stats for further processing
                    try:
                        heroStats = models.UserHeroStats.objects.get(user=userInstance,hero=hero)
                        heroStatsList = [{
                                'hero_id': hero.valveID,
                                'games': heroStats.games,
                                'win': heroStats.win,
                                'with_games': heroStats.with_games,
                                'with_win': heroStats.with_win,
                                'against_games': heroStats.against_games,
                                'against_win': heroStats.against_win,
                            }]
                    except Exception as e:
                        print(e)
                        heroStatsList = []

                # worst case, default to pro matchup data
                else:
                    print('DEFAULTING TO OD FOR PRO STATS')

                    # query OD for W/L/P/B
                    apiURLBaseStr = settings.OPENDOTA_API_URL
                    apiKey = settings.OPENDOTA_API_KEY
                    apiStr = '/'.join(['heroStats'])
                    queryStr = '{}/{}?api_key={}'.format(
                                            apiURLBaseStr,
                                            apiStr,
                                            apiKey
                                    )
                    queryRes = requests.get(queryStr)
                    if queryRes.status_code == 200:
                        queryJSON = queryRes.json()
                        heroStatsList = [{
                            'hero_id': hero.valveID,
                            'games': queryJSON['pro_pick'],
                            'win': queryJSON['pro_win'],
                            'with_games': 0,
                            'with_win': 0,
                            'against_games': 0,
                            'against_win': 0,
                        }]

                playerNGames = 0
                playerNGames_with = 0
                playerNGames_against = 0
                playerWinrate = 0
                playerWinrate_with = 0
                playerWinrate_against = 0

                for heroStats in heroStatsList:
                    if int(heroStats['hero_id']) == hero.valveID:
                        # unpack
                        playerNGames = heroStats['games']
                        playerNGames_with = heroStats['with_games']
                        playerNGames_against = heroStats['against_games']

                        # catch divide by zeros
                        if playerNGames > 0:
                            playerWinrate = heroStats['win'] / playerNGames
                        else:
                            playerWinrate = 0.
                        if playerNGames_with > 0:
                            playerWinrate_with = heroStats['with_win'] / playerNGames_with
                        else:
                            playerNGames_with = 0
                        if playerNGames_against > 0:
                            playerWinrate_against = heroStats['against_win'] / playerNGames_against
                        else:
                            playerWinrate_against = 0

                        break

                ## 2. store
                player_ngames_hero_list.append(playerNGames)
                player_ngames_with_hero_list.append(playerNGames_with)
                player_ngames_against_hero_list.append(playerNGames_against)

                player_winrate_hero_list.append(playerWinrate)
                player_winrate_with_hero_list.append(playerWinrate_with)
                player_winrate_against_hero_list.append(playerWinrate_against)

        # quality checks
        if len(player_ngames_hero_list) == 0:
            player_ngames_hero_list = [0.]

        if len(player_winrate_hero_list) == 0:
            player_winrate_hero_list = [0.]
        if len(meta_winrate_hero_list) == 0:
            meta_winrate_hero_list = [0.]

        if len(player_ngames_with_hero_list) == 0:
            player_ngames_with_hero_list = [0.]
        if len(player_winrate_with_hero_list) == 0:
            player_winrate_with_hero_list = [0.]

        if len(player_ngames_against_hero_list) == 0:
            player_ngames_against_hero_list = [0.]
        if len(player_winrate_against_hero_list) == 0:
            player_winrate_against_hero_list = [0.]

        ## 3. after loop, compute team stats, add to feature dict
        team_top_n_games_hero = np.array(player_ngames_hero_list).max()
        team_top_win_rate_hero = np.array(player_winrate_hero_list).max()
        team_top_meta_win_rate = np.array(meta_winrate_hero_list).max()

        team_average_ngames_hero = np.array(player_ngames_hero_list).mean()
        team_average_win_rate_hero = np.array(player_winrate_hero_list).mean()
        team_average_meta_win_rate = np.array(meta_winrate_hero_list).mean()

        team_top_n_games_with_hero = np.array(player_ngames_with_hero_list).max()
        team_top_win_rate_with_hero = np.array(player_winrate_with_hero_list).max()
        team_average_ngames_with_hero = np.array(player_ngames_with_hero_list).mean()
        team_average_win_rate_with_hero = np.array(player_winrate_with_hero_list).mean()

        team_top_n_games_against_hero = np.array(player_ngames_against_hero_list).max()
        team_top_win_rate_against_hero = np.array(player_winrate_against_hero_list).max()
        team_average_ngames_against_hero = np.array(player_ngames_against_hero_list).mean()
        team_average_win_rate_against_hero = np.array(player_winrate_against_hero_list).mean()


        team_stat_feature_dict = {
                'team_n_public': team_n_public,

                'team_top_n_games_hero': team_top_n_games_hero,
                'team_top_win_rate_hero': team_top_win_rate_hero,
                'team_top_meta_win_rate': team_top_meta_win_rate,

                'team_average_ngames_hero': team_average_ngames_hero,
                'team_average_win_rate_hero': team_average_win_rate_hero,
                'team_average_meta_win_rate': team_average_meta_win_rate,

                'team_top_n_games_with_hero': team_top_n_games_with_hero,
                'team_top_win_rate_with_hero': team_top_win_rate_with_hero,
                'team_average_ngames_with_hero': team_average_ngames_with_hero,
                'team_average_win_rate_with_hero': team_average_win_rate_with_hero,

                'team_top_n_games_against_hero': team_top_n_games_against_hero,
                'team_top_win_rate_against_hero': team_top_win_rate_against_hero,
                'team_average_ngames_against_hero': team_average_ngames_against_hero,
                'team_average_win_rate_against_hero': team_average_win_rate_against_hero,

            }

        for feature,statValue in team_stat_feature_dict.items():
            if feature in feature_list:
                featureDict[side][feature] = statValue

    ## 4. final clean up/aggregations
    radChatSent = np.array(featureDict['RADIANT']['chat_sentiment'])
    direChatSent = np.array(featureDict['DIRE']['chat_sentiment'])
    for key,item in {'RADIANT':radChatSent,'DIRE':direChatSent}.items():
        if len(item) > 0:
            featureDict[key]['chat_sentiment'] = item.mean()
        else:
            featureDict[key]['chat_sentiment'] = 0.

    return featureDict


def parse_cmd_args():
    ''' Parse the command line options '''

    # init parser
    descStr = 'Run some modeling on 1k matches'
    parser = argparse.ArgumentParser(description=descStr)
    conflictGroup_read = parser.add_mutually_exclusive_group()
    conflictGroup_model = parser.add_mutually_exclusive_group()

    # optional
    parser.add_argument('-v','--verbose',
                        help='print diagnostic info',action='store_true')

    conflictGroup_read.add_argument('-r','--read-new-data',
                        help='Read new data from the DB', action='store_true')
    conflictGroup_read.add_argument('-i','--infile',type=str,
                        help='CSV to read in')

    parser.add_argument('-p','--plot',
                        help='Save plot to disk',action='store_true')
    parser.add_argument('--plot-file',type=str,
                        help='File to save plot')

    parser.add_argument('-s','--save',
                        help='Save DataFrame to CSV',action='store_true')
    parser.add_argument('-o','--outfile',type=str,
                        help='CSV to write out')

    parser.add_argument('-m','--model-save-file',type=str,
                        help='Save model to pickle file')
    parser.add_argument('-l','--model-load-file',type=str,
                        help='Load model from pickle file')

    parser.add_argument('--date-min',
                        help='Include matches after this date')
    parser.add_argument('--date-max',
                        help='Include matches before this date')
    parser.add_argument('--full-random', action='store_true',
                        help='Completely random matches, no random seed')

    parser.add_argument('--query-open-dota',
                        help='Query the OpenDota API for stats',action='store_true')

    conflictGroup_model.add_argument('--logistic-regression',
                                help='Run modeling with LogisticRegression', action='store_true')
    conflictGroup_model.add_argument('--xgboost',
                                help='Run modeling with XGBoost',action='store_true')

    parser.add_argument('-n','--nsamp',type=int,
                        help='Number of games to sample')
    parser.add_argument('--skip-player-stats',
                        help='Skip analysis of player stats',action='store_true')
    parser.add_argument('--no-squash',
                        help='Do not squash rows into 1 row per game',action='store_true')

    # parse
    cmdArgs = parser.parse_args()

    args = ()

    kwargs = {}

    kwargs['VERBOSE'] = cmdArgs.verbose
    kwargs['READ_NEW_DATA'] = cmdArgs.read_new_data
    kwargs['INFILE'] = cmdArgs.infile
    kwargs['PLOT'] = cmdArgs.plot
    kwargs['PLOT_FILE'] = cmdArgs.plot_file
    kwargs['SAVE'] = cmdArgs.save
    kwargs['OUTFILE'] = cmdArgs.outfile
    kwargs['MODEL_SAVE_FILE'] = cmdArgs.model_save_file
    kwargs['MODEL_LOAD_FILE'] = cmdArgs.model_load_file
    kwargs['DATE_MIN'] = cmdArgs.date_min
    kwargs['DATE_MAX'] = cmdArgs.date_max
    kwargs['FULL_RANDOM'] = cmdArgs.full_random
    kwargs['QUERY_OPEN_DOTA'] = cmdArgs.query_open_dota
    kwargs['LOGISTIC_REGRESSION'] = cmdArgs.logistic_regression
    kwargs['XGBOOST'] = cmdArgs.xgboost

    kwargs['NSAMP'] = cmdArgs.nsamp
    kwargs['SKIP_PLAYER_STATS'] = cmdArgs.skip_player_stats
    kwargs['NO_SQUASH'] = cmdArgs.no_squash

    return (args,kwargs)





def main(*args,**kwargs):
    '''
    Plot various feature importances
    '''

    VERBOSE = kwargs.get('VERBOSE')
    READ_NEW_DATA = kwargs.get('READ_NEW_DATA')
    INFILE = kwargs.get('INFILE')
    PLOT = kwargs.get('PLOT')
    PLOT_FILE = kwargs.get('PLOT_FILE')
    SAVE = kwargs.get('SAVE')
    OUTFILE = kwargs.get('OUTFILE')
    MODEL_SAVE_FILE = kwargs.get('MODEL_SAVE_FILE')
    MODEL_LOAD_FILE = kwargs.get('MODEL_LOAD_FILE')
    DATE_MIN = kwargs.get('DATE_MIN')
    DATE_MAX = kwargs.get('DATE_MAX')
    FULL_RANDOM = kwargs.get('FULL_RANDOM')
    QUERY_OPEN_DOTA = kwargs.get('QUERY_OPEN_DOTA')
    LOGISTIC_REGRESSION = kwargs.get('LOGISTIC_REGRESSION')
    XGBOOST = kwargs.get('XGBOOST')

    nSamp = kwargs.get('NSAMP',100)
    SKIP_PLAYER_STATS = kwargs.get('SKIP_PLAYER_STATS')
    NO_SQUASH = kwargs.get('NO_SQUASH')

    if (PLOT) and (not PLOT_FILE):
        PLOT_FILE = 'dummyPlot.png'
    if (SAVE) and (not OUTFILE):
        OUTFILE = 'xDF_{}.csv'.format(datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S'))


    if not LOGISTIC_REGRESSION and not XGBOOST:
        errString = 'You must chose a modeling method!'
        print(errString)
        sys.exit(1)
    if not READ_NEW_DATA and not INFILE:
        errString = 'You must specify a data source!'
        print(errString)
        sys.exit(1)

    heroFeatureList = [
            'matchID', # important
            'num_carry',
            'num_support',
            'num_escape',
            'num_durable',
            'num_pusher',
            'num_initiator',
            'chat_sentiment',
        ]

    skillFeatureList = [
            'num_passive',
            'num_autocast',
            'num_attack_modifier',
            'num_disable',
            'num_channel_cancelling',
            'num_hard_disable',
            'num_channeled',
            'num_channeled_cast',
            'num_bash',
            'num_grants_invisibility',
            'num_grants_true_sight',
            'num_heals_teammates',
            'num_aoe_denial',
            'num_provides_miss_chance',
        ]

    teamFeatureList = [
            'team_n_public',
            'team_top_n_games_hero',
            'team_top_win_rate_hero',
            'team_top_meta_win_rate',

            'team_average_ngames_hero',
            'team_average_win_rate_hero',
            'team_average_meta_win_rate'

            # cross terms on the hero interactions
            # note: need to implement some cacheing before using this in production
            # since calculating this on the fly is painful

            # 'team_top_n_games_with_hero',
            # 'team_top_win_rate_with_hero',
            # 'team_average_ngames_with_hero',
            # 'team_average_win_rate_with_hero',

            # 'team_top_n_games_against_hero',
            # 'team_top_win_rate_against_hero',
            # 'team_average_ngames_against_hero',
            # 'team_average_win_rate_against_hero',
        ]

    feature_list = heroFeatureList + skillFeatureList + teamFeatureList

    # for each game, calcuate the features
    if READ_NEW_DATA:

        dfCols = ['win']
        dfCols += [feature for feature in feature_list]
        xDF = pd.DataFrame(columns=dfCols)

        if (DATE_MIN and not DATE_MAX) or (not DATE_MIN and DATE_MAX):
            errString = 'You didn\'t supply both a min and max date! Exiting...'
            print(errString)
            sys.exit(1)

        # grab users from a specific day
        if DATE_MIN and DATE_MAX:

            # really should split this up into a list of 1 QuerySet per hour
            start_query = datetime.datetime.strptime(DATE_MIN,'%Y-%m-%d').timestamp()
            end_query = datetime.datetime.strptime(DATE_MAX,'%Y-%m-%d').timestamp()
            match_queryset = models.Match.objects.all()
            match_queryset = match_queryset.filter(
                                start_time__gte=start_query, 
                                start_time__lte=end_query
                            )
        else:
            # DO NOT DO THIS IN PRODUCTION LOL
            # get all stored matches
            match_queryset = models.Match.objects.all()

        # sample 1000 random games
        allIDs = list(match_queryset.values('id'))
        if not FULL_RANDOM:
            np.random.seed(0)
        randInds = np.random.randint(len(allIDs),size=nSamp)
        randGameIDs = [allIDs[ind]['id'] for ind in randInds]
        randomGames_queryset = models.Match.objects.filter(id__in=randGameIDs)

        # populate xDF from actual data
        for i,game in enumerate(randomGames_queryset):

            outStr = 'Working on {} out of {} games'.format(i,nSamp)
            print(outStr)

            rowIndex = i*2

            featureDictBothSides = calculate_features(game,feature_list=feature_list,
                                                        QUERY_OPEN_DOTA=QUERY_OPEN_DOTA,
                                                        SKIP_PLAYER_STATS=SKIP_PLAYER_STATS)
            radiantDict = featureDictBothSides['RADIANT']
            direDict = featureDictBothSides['DIRE']

            radiantData = pd.Series(radiantDict)
            direData = pd.Series(direDict)
            xDF.loc[rowIndex] = radiantData
            xDF.loc[rowIndex+1] = direData

        # always by default squash the data into one single row per game
        if not NO_SQUASH:
            newDF = pd.DataFrame(columns=xDF.columns)
            # unparse into match specific features
            for i in range(int(xDF.shape[0]/2)):
                rowIndex = i*2
                radRow = xDF.loc[rowIndex]
                direRow = xDF.loc[rowIndex+1]

                excludeList = ['win','matchID']
                relDict = {}

                for colName in excludeList:
                    relDict[colName] = radRow[colName]

                for colName in feature_list:
                    if colName not in excludeList:
                        relDict[colName] = radRow[colName] - direRow[colName]

                relData = pd.Series(relDict)
                newDF.loc[i] = relData
            xDF = newDF

    else:
        # else just read xDF from a csv
        xDF = pd.read_csv(INFILE)

        for col in xDF.columns:
            if col not in feature_list and col != 'win':
                xDF.pop(col)

    if SAVE:
        xDF.to_csv(OUTFILE,index=False)

    ### Data ingestion finished, now dive into the modeling ###

    # extract target values, train-test-split, kfold, etc here
    trash_matchID = xDF.pop('matchID')
    yArr = xDF.pop('win').values.astype(int)
    xArr = xDF.values

    try:

        if LOGISTIC_REGRESSION:

            # Note, I don't really care about feature scaling etc, just trying to
            # do a quick and dirty sanity check here, don't need the full
            # blown feature importance breakdown etc. and I'm favoring XGB anyway

            # train test split
            xtrain,xtest,ytrain,ytest = train_test_split(
                                                xArr, yArr, 
                                                test_size=0.25, 
                                                random_state=42
                                            )

            if MODEL_LOAD_FILE:
                bestModel = pickle.load(open(MODEL_LOAD_FILE, 'rb'))
            else:
                # init train predict test
                logReg = LogisticRegression(
                            random_state=0, solver='liblinear',
                            multi_class='ovr',max_iter=10000)

                test_params = {
                        'penalty':['l1','l2'],
                        'C':np.logspace(0, 4, 10),
                    }

                bestModel = GridSearchCV(
                                cv=5, 
                                scoring='roc_auc',
                                estimator = logReg,
                                param_grid = test_params,
                                verbose=True,
                                refit=True
                            )
                bestModel.fit(xtrain,ytrain)

            # validation
            ypred=bestModel.predict(xtest)

            print("Accuracy:",metrics.accuracy_score(ytest, ypred))
            print("Precision:",metrics.precision_score(ytest, ypred))
            print("Recall:",metrics.recall_score(ytest, ypred))

            cnf_matrix = metrics.confusion_matrix(ytest, ypred)
            class_names=['Loss','Win'] # name  of classes
            fig, ax = plt.subplots()
            tick_marks = np.arange(len(class_names))

            plt.xticks(tick_marks, class_names, fontsize=18)
            plt.yticks(tick_marks, class_names, fontsize=18)

            # create heatmap
            sns.heatmap(pd.DataFrame(cnf_matrix), annot=True, cmap="YlGnBu" ,fmt='g',
                        xticklabels=['Win','Loss'],yticklabels=['Win','Loss'])
            plt.ylabel('Actual', fontsize=20)
            plt.xlabel('Predicted', fontsize=20)

            plt.show()

            ypred_proba = bestModel.predict_proba(xtest)[::,1]
            fpr, tpr, _ = metrics.roc_curve(ytest,  ypred_proba)
            auc = metrics.roc_auc_score(ytest, ypred_proba)
            plt.plot(fpr,tpr,label="data 1, auc="+str(auc))
            plt.legend(loc=4)
            plt.show()

            if MODEL_SAVE_FILE:
                # save model to file
                pickle.dump(bestModel, open(MODEL_SAVE_FILE, 'wb'))

        # fit XGBoost
        if XGBOOST:

            # train test split
            xtrain,xtest,ytrain,ytest = train_test_split(
                                                xArr, yArr, 
                                                test_size=0.25, 
                                                random_state=42
                                            )

            if MODEL_LOAD_FILE:
                bestModel = pickle.load(open(MODEL_LOAD_FILE, 'rb'))
            else:

                # init the classifier
                xgClass = xgb.XGBClassifier(
                                    objective ='binary:logistic', 
                                    colsample_bytree = 0.3, 
                                    learning_rate = 0.1,
                                    max_depth = 5, 
                                    alpha = 10, 
                                    n_estimators = 10,
                                )

                # grid search params
                test_params = {
                        'objective':['binary:logistic'],
                        'learning_rate': [0.03,0.05,0.1], #so called `eta` value
                        'max_depth': [6,7,8],
                        'min_child_weight': [1,5,10],
                        'gamma': [1, 1.5],
                        'silent': [1],
                        'subsample': [0.5,0.8],
                        'colsample_bytree': [0.5,0.8],
                        'n_estimators': [20, 50, 300], #number of trees
                        'missing':[-999],
                        'seed': [1337]
                    }

                # quick test fit params
                # test_params = {
                #         'objective':['binary:logistic'],
                #         'learning_rate': [0.05,], #so called `eta` value
                #         'max_depth': [7],
                #         'min_child_weight': [5],
                #         'gamma': [1.5],
                #         'silent': [1],
                #         'subsample': [0.8],
                #         'colsample_bytree': [0.8],
                #         'n_estimators': [50, 100], #number of trees
                #         'missing':[-999],
                #         'seed': [1337]
                #     }

                bestModel = GridSearchCV(
                                cv=5, 
                                scoring='roc_auc',
                                estimator = xgClass,
                                param_grid = test_params,
                                verbose=True,
                                refit=True
                            )
                bestModel.fit(xtrain,ytrain)

            # validation
            ypred = bestModel.predict(xtest) # should be test data

            print("Accuracy:",metrics.accuracy_score(ytest, ypred))
            print("Precision:",metrics.precision_score(ytest, ypred))
            print("Recall:",metrics.recall_score(ytest, ypred))

            cnf_matrix = metrics.confusion_matrix(ytest, ypred)
            class_names=[0,1] # name  of classes
            fig, ax = plt.subplots()
            tick_marks = np.arange(len(class_names))
            plt.xticks(tick_marks, class_names, fontsize=18)
            plt.yticks(tick_marks, class_names, fontsize=18)

            # create heatmap
            sns.heatmap(pd.DataFrame(cnf_matrix), annot=True, cmap="YlGnBu" ,fmt='g',
                        xticklabels=['Win','Loss'],yticklabels=['Win','Loss'],
                        annot_kws={"size": 20})
            plt.ylabel('Actual', fontsize=20)
            plt.xlabel('Predicted', fontsize=20)
            plt.show()

            ypred_proba = bestModel.predict_proba(xtest)[::,1]
            fpr, tpr, _ = metrics.roc_curve(ytest,  ypred_proba)
            auc = metrics.roc_auc_score(ytest, ypred_proba)
            plt.plot(fpr,tpr,label="data 1, auc="+str(auc))
            plt.legend(loc=4)
            plt.show()


            # print important feature names
            outStr = '\n'
            featInd = 0
            tick_label=[]
            featBarDict = {}
            importanceDict = bestModel.best_estimator_.get_booster().get_score()

            for col in xDF.columns:
                if 'f{}'.format(featInd) in importanceDict:
                    tick_label.append(col)
                    outStr += 'f{} is {}\n'.format(featInd,col)
                    featBarDict[col] = importanceDict['f{}'.format(featInd)]
                featInd += 1
            print(outStr)

            # xg vis
            # xgb.plot_tree(bestModel.best_estimator_,num_trees=0)
            # plt.show()
            xgb.plot_importance(bestModel.best_estimator_)
            plt.show()


            # make a nice histogram
            fig, ax = plt.subplots(figsize=(10,6))
            sns.set(style="whitegrid")

            # turn this into vectors to make my life easier
            barX = []
            barY = []
            featBarTupList = sorted(featBarDict.items(),key=lambda x: x[1],reverse=True)
            for key,val in featBarTupList:
                barX.append(val) 
                barY.append(key)
            sns.barplot(x=barX, y=barY, 
                        color="#348feb"
                    )

            # tick labels
            for t in ax.yaxis.get_ticklabels():
                t.set_fontsize(16)
            ax.get_xaxis().set_ticks([])
            # axis labels
            plt.xlabel('Relative Importance', fontsize=20)
            plt.subplots_adjust(left=0.3)

            plt.show()


            if MODEL_SAVE_FILE:
                # save model to file
                pickle.dump(bestModel, open(MODEL_SAVE_FILE, 'wb'))

    except Exception as e:
        print(e)
        pdb.set_trace()

    return 0



if __name__ == '__main__':
    ''' Run parsing, then main '''
    args,kwargs = parse_cmd_args()
    main(*args,**kwargs)
