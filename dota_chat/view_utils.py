import os,sys,shutil,pdb,glob,logging,datetime,time,json,random,pickle,copy
from collections import OrderedDict
import numpy as np 
import pandas as pd
import scipy as scipy
from scipy import special

import requests

from . import models as models
from . import constants as dc_constants
from django.db.models import Avg, Count
from django.conf import settings
from django.http import HttpResponse, JsonResponse 
from django.http import HttpResponseRedirect, HttpResponseServerError, HttpResponseForbidden
from django.urls import reverse
from django.urls import reverse, reverse_lazy

import bokeh.plotting as bp
from bokeh.resources import CDN
from bokeh.embed import file_html
from bokeh.models import ColumnDataSource,Range1d,Span,LinearAxis,Label,Title,HoverTool,GMapOptions,LinearColorMapper
from bokeh.models.markers import Circle
from bokeh.models.glyphs import ImageURL
from bokeh.core.properties import FontSizeSpec
from bokeh.layouts import gridplot
from bokeh.palettes import Spectral6,Plasma
from bokeh.transform import factor_cmap,transform


from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.plotting import figure, ColumnDataSource
import colorcet as cc

import xgboost as xgb

from matplotlib import pyplot as plt

logger = logging.getLogger(__name__)



def query_opendota_api_route_args(routeArgs,**kwargs):
    '''
    Query OpenDota (GET /{route}/{key})

    Parameters
    ----------
    routeArgs : list
        list of string url components (e.g., ['matches',19,'matchups'])

    Returns
    -------
    dict : A dictionary populated with JSON decoded response

    '''

    try:
        apiURLBaseStr = settings.OPENDOTA_API_URL
        apiKey = settings.OPENDOTA_API_KEY
        apiStr = '/'.join(routeArgs)
        queryStr = '{}/{}?api_key={}'.format(
                                apiURLBaseStr,
                                apiStr,
                                apiKey
                        )
        queryRes = requests.get(queryStr)

    except Exception as e:
        errStr = 'Query failed {}'.format(e)
        logger.error(errStr)
        queryRes = requests.Response()
        queryRes.status_code = 500
        #pdb.set_trace()

    dataDict = queryRes.json()

    # passively prevent rate exceeding if many queries
    time.sleep(kwargs.get('sleepTime',0.05)) 

    return dataDict




def winRatePlot(request,hero_id,USE_PRO=False):

    # assemble data
    heroInstance = models.Hero.objects.get(valveID=hero_id)

    # query OD for W/L/P/B
    args = ['heroStats']
    heroStatsList = query_opendota_api_route_args(args,sleepTime=0.)

    if USE_PRO:
        targetID = heroInstance.valveID

        for heroEntry in heroStatsList:
            if heroEntry['hero_id'] == targetID:
                picks = heroEntry['pro_pick']
                bans = heroEntry['pro_ban']
                wins = heroEntry['pro_win']
                losses = picks - wins
                break
    else:
        wins = len(models.Player.objects.filter(
                            hero=heroInstance,
                            wonMatch=True
                        )
                    )
        losses = len(models.Player.objects.filter(
                            hero=heroInstance,
                            wonMatch=False
                        )
                    )

    xLabels = ['Win','Loss']
    colors = ['#24ba1c','#ba1c1c']

    try:
        wlRates = [wins/(wins+losses),losses/(wins+losses)]
    except Exception as e:
        wlRates = [0.,0.]

    # configure plotting
    bokehAx=bp.figure(x_range=xLabels,plot_width=325,sizing_mode='scale_height')
    bokehAx.toolbar.logo = None
    bokehAx.toolbar_location = None
    bokehAx.vbar(x=xLabels, top=wlRates, width=0.25,fill_color=colors)

    bokehAx.title.text = ''
    bokehAx.xaxis.axis_label = ''
    bokehAx.yaxis.axis_label = 'Rate'
    plotResponse = file_html(bokehAx,CDN,'winRatePlot')

    # return
    return HttpResponse(plotResponse)


def winLossChatPlot(request,hero_id):

    # assemble data
    heroInstance = models.Hero.objects.get(valveID=hero_id)
    args = ['heroes',str(heroInstance.valveID),'matchups']

    # list of dicts sorted by n_matches keyed on heroID
    # {'hero_id': 56, 'games_played': 6, 'wins': 6}
    heroMatchupData = query_opendota_api_route_args(args,sleepTime=0.)

    TOOLTIPS = [
        ('Hero', '@hero'),
        ('Win, Loss', '($x{int}, $y{int})'),
    ]
    
    TOOLS = 'pan,wheel_zoom,box_zoom,reset'


    # init scatter plot
    bokehAx = bp.figure(width=750,sizing_mode='scale_height',tools=TOOLS)

    sourceDict = {
        'url': [],
        'x': [],
        'y': [],
        'hero':[],
    }

    # populate the source dict with matchup data
    for matchupDict in heroMatchupData:
        heroMatchup = models.Hero.objects.get(valveID=matchupDict['hero_id'])
        heroIconURL = heroMatchup.get_absolute_image_url
        heroIconURL = request.build_absolute_uri(heroMatchup.icon.url)
        nGames = matchupDict['games_played']
        nWins = matchupDict['wins']
        nLosses = nGames - nWins

        sourceDict['url'].append(heroIconURL)
        sourceDict['x'].append(nWins)
        sourceDict['y'].append(nLosses)
        sourceDict['hero'].append(heroMatchup.prettyName)

    # plot it
    source = ColumnDataSource(sourceDict)

    # HoverTool doesn't work with ImageURL, so plot transparent glyphs
    circle_glyph = Circle(x='x',y='y',size=10,
                            line_color='white',fill_color='white',
                            line_alpha=1.,fill_alpha=1.)
    circle_renderer = bokehAx.add_glyph(source,circle_glyph)

    icon = ImageURL(url='url', x='x', y='y', w=None, h=None, anchor="center")
    bokehAx.add_glyph(source,icon)

    # tooltips
    hover = HoverTool(renderers=[circle_renderer],tooltips=TOOLTIPS)
    bokehAx.tools.append(hover)

    # labels etc
    bokehAx.title.text = ''
    bokehAx.xaxis.axis_label = 'Wins (professional games)'
    bokehAx.yaxis.axis_label = 'Losses (professional games)'
    plotResponse = file_html(bokehAx,CDN,'winLossChatPlot')

    return HttpResponse(plotResponse)



def make_histogram_plot(title, hist, edges, x, pdf, cdf):
    p = bp.figure(title=title, tools='', background_fill_color="#fafafa")
    p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
           fill_color="navy", line_color="white", alpha=0.5)
    p.line(x, pdf, line_color="#ff8888", line_width=4, alpha=0.7, legend="PDF")
    p.line(x, cdf, line_color="orange", line_width=2, alpha=0.7, legend="CDF")

    p.y_range.start = 0
    p.legend.location = "center_right"
    p.legend.background_fill_color = "#fefefe"
    p.xaxis.axis_label = 'x'
    p.yaxis.axis_label = 'Pr(x)'
    p.grid.grid_line_color="white"
    return p

def make_histogram_plot_only(title,hist,edges,xlabel=None,ylabel=None):

    if xlabel is not None:
        xlabel = xlabel
    else:
        xlabel = 'Quantity'
    if ylabel is not None:
        ylabel = ylabel
    else:
        ylabel = 'Count'

    bokehAx = bp.figure(title=title, tools='', background_fill_color="#fafafa")
    bokehAx.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
           fill_color=cc.bgy[100], line_color="white")
    #p.line(x, pdf, line_color="#ff8888", line_width=4, alpha=0.7, legend="PDF")
    #p.line(x, cdf, line_color="orange", line_width=2, alpha=0.7, legend="CDF")

    bokehAx.title.text_font_size = '18pt'

    bokehAx.xaxis.axis_label_text_font_style = 'normal'
    bokehAx.xaxis.axis_label_text_font_size = '15pt'
    bokehAx.xaxis.axis_label_text_font_size = '15pt'
    bokehAx.xaxis.major_label_text_font_size = '15pt'

    bokehAx.yaxis.axis_label_text_font_style = 'normal'
    bokehAx.yaxis.axis_label_text_font_size = '15pt'
    bokehAx.yaxis.axis_label_text_font_size = '15pt'
    bokehAx.yaxis.major_label_text_font_size = '15pt'
    bokehAx.y_range.start = 0

    bokehAx.xaxis.axis_label = xlabel
    bokehAx.yaxis.axis_label = ylabel
    bokehAx.grid.grid_line_color="white"

    return bokehAx



def temporal_histograms(request):

    # start times
    allMatches = models.Match.objects.values('start_time','duration').all()
    startTimes = [match['start_time'] for match in allMatches]
    durationTimes = [match['duration'] for match in allMatches]

    startTimes = np.array(startTimes)
    durationTimes = np.array(durationTimes) / 60.

    startTimes = startTimes - startTimes.min()
    startTimes = startTimes / 60. / 60.

    # Start times
    hist, edges = np.histogram(startTimes, density=False, bins=48)
    p1 = make_histogram_plot_only(
                'Match Start', hist, edges,
                xlabel='Hour + const.',
                ylabel='Relative Count')

    # Duration times
    hist, edges = np.histogram(durationTimes, density=False, bins=48)
    p2 = make_histogram_plot_only(
                'Match Duration', hist, edges,
                xlabel='Duration [minutes]',
                ylabel='Relative Count')

    bokehAx = gridplot([p1,p2], 
                ncols=2, sizing_mode='stretch_width', toolbar_location=None)
    plotResponse = file_html(bokehAx,CDN,'hist')

    return HttpResponse(plotResponse)

def hero_popularity_histogram(request):

    # all matches
    allHeros = models.Hero.objects.all()
    allPlayers = models.Player.objects.all()

    heroCountDict = {}
    heroList = []
    countList = []
    for hero in allHeros:
        heroCount = models.Player.objects.filter(hero__valveID=hero.valveID).count()
        heroCountDict[hero.prettyName] = heroCount

    # to list
    for hero,count in heroCountDict.items():
        heroList.append(hero)
        countList.append(count)

    # sort
    heroList = [hero for trash, hero 
                    in sorted(zip(countList,heroList),
                    key=lambda tup: tup[0],
                    reverse=True)]
    countList = sorted(countList,reverse=True)

    # plot
    source = ColumnDataSource(data=dict(heroList=heroList, counts=countList))
    colors = [cc.bgy[i*2] for i in range(len(heroList))]
    mapper = LinearColorMapper(palette=colors, low=np.min(countList), high=np.max(countList))


    bokehAx = bp.figure(x_range=heroList, sizing_mode='stretch_width', 
                        toolbar_location='right', title='Hero Popularity',
                        tools='pan,wheel_zoom,box_zoom,reset')
    bokehAx.vbar(x='heroList', top='counts', width=0.9, 
                 source=source,
                 line_color='white', 
                 fill_color=transform('counts', mapper)
        )


    bokehAx.add_tools(
        HoverTool(
            tooltips=[("Hero", "@heroList"), ("Games", "@counts")],
            mode='vline'
            )
        )

    bokehAx.title.text_font_size = '18pt'
    bokehAx.xgrid.grid_line_color = None
    bokehAx.yaxis.axis_label_text_font_style = 'normal'
    bokehAx.yaxis.axis_label_text_font_size = '16pt'
    bokehAx.xaxis.major_label_orientation = np.pi/2.

    bokehAx.y_range.start = 0
    bokehAx.yaxis.axis_label = 'Relative Count'
    bokehAx.yaxis.axis_label_text_font_style = 'normal'
    bokehAx.yaxis.axis_label_text_font_size = '15pt'
    bokehAx.yaxis.axis_label_text_font_size = '15pt'
    bokehAx.yaxis.major_label_text_font_size = '15pt'

    plotResponse = file_html(bokehAx,CDN,'hist')

    return HttpResponse(plotResponse)


def region_histogram(request):

    # all matches
    regionDict = dc_constants.region_dict
    regionCount_queryset = models.Match.objects.values('region').annotate(count=Count('region'))

    regionKeyList = []
    regionList = []
    countList = []
    for qsDict in regionCount_queryset:
        if qsDict['region'] is not None:
            regionKeyList.append(qsDict['region'])
            regionList.append(regionDict[str(qsDict['region'])])
            countList.append(qsDict['count'])

    # sort
    regionList = [region for trash, region 
                    in sorted(zip(countList,regionList),
                    key=lambda tup: tup[0],
                    reverse=True)]
    countList = sorted(countList,reverse=True)

    # plot
    source = ColumnDataSource(data=dict(regionList=regionList, counts=countList))
    colors = [cc.bgy[i*12] for i in range(len(regionList))]
    mapper = LinearColorMapper(palette=colors, low=np.min(countList), high=np.max(countList))


    bokehAx = bp.figure(x_range=regionList, sizing_mode='stretch_width', 
                        toolbar_location=None, title="Region Popularity")
    bokehAx.vbar(x='regionList', top='counts', width=0.9, 
                 source=source,
                 line_color='white', 
                 fill_color=transform('counts', mapper)
        )


    bokehAx.add_tools(
        HoverTool(
            tooltips=[("Region", "@regionList"), ("Games", "@counts")],
            mode='vline'
            )
        )

    bokehAx.title.text_font_size = '18pt'

    bokehAx.xgrid.grid_line_color = None
    bokehAx.xaxis.major_label_orientation = np.pi/2./2.
    bokehAx.xaxis.axis_label_text_font_size = '15pt'
    bokehAx.xaxis.major_label_text_font_size = '15pt'

    bokehAx.yaxis.axis_label = 'Relative Count'
    bokehAx.yaxis.axis_label_text_font_style = 'normal'
    bokehAx.yaxis.axis_label_text_font_size = '15pt'
    bokehAx.yaxis.major_label_text_font_size = '15pt'
    bokehAx.y_range.start = 0

    plotResponse = file_html(bokehAx,CDN,'hist')

    return HttpResponse(plotResponse)



def generateRandomDraft(n_heros=10,VERBOSE=False):
    '''
    Use the current meta to generate a random hero draft
    '''

    allPickCount = models.Player.objects.all().count()
    allHeros = models.Hero.objects.all()

    # init
    cumulativeProb = 0.
    heroRateDict = {'null':0.}
    heroProbDict = OrderedDict()
    heroDraft = []
    countList = []

    # get a list of all hero pick rates
    for hero in allHeros:
        heroRate = 1.*models.Player.objects.filter(hero__valveID=hero.valveID).count() / float(allPickCount)
        cumulativeProb += heroRate
        heroRateDict[hero.slug] = cumulativeProb

    # make a ordered dict of key,val = cumulativeProb, heroName
    for hero in sorted(heroRateDict, key=heroRateDict.get):
        heroProbDict[heroRateDict[hero]] = hero

    # now randomly draw from this dist until you have 10 unique heros
    rateKeys = list(heroProbDict.keys())
    while len(heroDraft) < n_heros:

        rand = np.random.random() # random
        keyInd = 0

        # march up thru keys until random draw is in hero pick rate interval
        for i,rate in enumerate(rateKeys):
            try:
                if rand >= rateKeys[i] and rand < rateKeys[i+1]:
                    draftedHero = heroProbDict[rateKeys[i+1]]
                    break
            except Exception as e:
                print(e)

        if draftedHero not in heroDraft:
            heroDraft.append(draftedHero)


    if VERBOSE:
        outStr = '\n'
        i = 1
        for hero in heroDraft:
            outStr += '{:>2}. {}\n'.format(i,hero)
            i += 1
        print(outStr)

    return heroDraft

def predictHeroPick(cleanFormData):

    heroDraftDict = OrderedDict()
    userDraftDict = OrderedDict()
    pickedHeroList = []

    heroFeatureList = [
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

            #'team_top_n_games_with_hero',
            #'team_top_win_rate_with_hero',
            #'team_average_ngames_with_hero',
            #'team_average_win_rate_with_hero',

        ]

    feature_list = heroFeatureList + skillFeatureList + teamFeatureList

    # parse heros
    for key,val in cleanFormData.items():
        if '_hero' in key:
            if val != '':
                heroDraftDict[key] = models.Hero.objects.get(valveID=int(cleanFormData[key]))
            else:
                heroDraftDict[key] = ''

    # parse users
    for key,val in cleanFormData.items():
        if '_user' in key:

            if val != '':

                # try to get each user from OpenDota, if it doesn't exist/not public
                # then just leave an empty string and we'll fill it with a dummy later
                try:
                    account_id = val.split('(ACCT ID: ')[1][:-1]
                    userInstance,userCreated = models.SteamUser.objects.get_or_create(
                                                    valveID=int(account_id),
                                                    defaults={'name':'STEAMID_{}'.format(account_id)}
                                        )
                    userDraftDict[key] = userInstance.valveID
                except Exception as e:
                    userDraftDict[key] = ''
            else:
                userDraftDict[key] = ''

    # populate heros from distribution where needed
    randomDraftList = generateRandomDraft()

    for key,val in heroDraftDict.items():
        if val != '':
            pickedHeroList.append(val.slug)

    for key,val in heroDraftDict.items():
        if val == '':
            for randomHeroSlug in randomDraftList:
                if randomHeroSlug not in pickedHeroList:
                    randomHero = models.Hero.objects.get(slug=randomHeroSlug)
                    heroDraftDict[key] = randomHero
                    pickedHeroList.append(randomHeroSlug)
                    break

    # populate users where needed?
    if userDraftDict['myTeamSlot1_user'] != '':
        user = userDraftDict['myTeamSlot1_user']
    else:
        user = None
    # no, we'll just leave it blank and in the feature calculation I'll pull
    # the hero winrate from the current meta

    # load model
    mlModel = pickle.load(open('dota_chat/ml_models/myXGBoostModel.pkl', 'rb'))
    #mlModel = pickle.load(open('dota_chat/ml_models/myLogRegModel.pkl', 'rb'))

    # compute features (first do static features, then update with )
    featureDict_incomplete = compute_features(
                                    heroDraftDict,
                                    userDraftDict,
                                    feature_list=feature_list
                                )

    # for each possible hero choice, calculate winProb
    allHeros = models.Hero.objects.all()
    winProbDict = OrderedDict()
    for hero in allHeros:
        if hero.slug not in pickedHeroList:

            heroDraftDict['myTeamSlot1_hero'] = hero


            featureDict = update_features(
                                featureDict_incomplete,
                                add_hero=hero,
                                add_user=user
                            )

            print(featureDict)

            # squash
            radiantDict = featureDict['RADIANT']
            direDict = featureDict['DIRE']

            radiantData = pd.Series(radiantDict)
            direData = pd.Series(direDict)

            #feature_list = list(featureDict['RADIANT'].keys())
            dfCols = [feature for feature in feature_list]

            # squash into one side
            relDict = OrderedDict()
            xDF = pd.DataFrame(columns=dfCols)

            for colName in feature_list:
                relDict[colName] = radiantData[colName] - direData[colName]

            relData = pd.Series(relDict)
            xDF.loc[0] = relData

            # predict
            winProb = mlModel.predict_proba(xDF.values)[0][1]
            #winProb = mlModel.predict_proba(xDF.values)[::,1] # for logreg

            winProbDict[hero.slug] = winProb

    sortList = sorted(winProbDict.items(), key=lambda x: x[1])
    outStr = ''
    for hero,prob in sortList:
        outStr += '{} has odds {}\n'.format(hero,prob)
    logger.info(outStr)

    return sortList


def update_features(featureDict_incomplete,add_hero,add_user=None):

    # deep copy
    featureDict = copy.deepcopy(featureDict_incomplete)
    feature_list = list(featureDict['RADIANT'].keys())

    # get the hero model
    hero = add_hero
    roles = hero.roles.all()
    abilities = hero.abilities.all()

    # assemble behavior list for this hero
    behaviorList = []
    for ability in abilities:
        for behavior in ability.behavior.all():
            behaviorList.append(behavior.behavior.lower().replace(' ','_'))


    ### Adjust all the metrics that are simple counts ###

    # capture role and ability behavior features
    for feature in feature_list:
        # loop over roles, add role-based features
        for role in roles:
            if '_'.join(feature.split('_')[1:]).lower() == role.role.lower():
                try:
                    featureDict['RADIANT'][feature] += 1
                except KeyError:
                    print('Key {} not in featureDict'.format(feature))

        # now loop over abilities, add ability-based features
        for behavior in behaviorList:
            if '_'.join(feature.split('_')[1:]).lower() == behavior.lower():
                try:
                    featureDict['RADIANT'][feature] += 1
                except KeyError:
                    print('Key {} not in featureDict'.format(feature))

    ### Adjust all the features that are hero based simple averages ###
    if 'chat_sentiment' in feature_list:
        newAverage = 4.*featureDict['RADIANT']['chat_sentiment']
        newAverage += hero.metaWinRate
        newAverage /= 5.
        featureDict['RADIANT']['chat_sentiment'] = newAverage
    if 'team_average_meta_win_rate' in feature_list:
        newAverage = 4.*featureDict['RADIANT']['team_average_meta_win_rate']
        newAverage += hero.metaWinRate
        newAverage /= 5.
        featureDict['RADIANT']['team_average_meta_win_rate'] = newAverage

    if add_user is not None and add_user != '':

        ### Adjust the features that are user specific averages ###
        user = models.SteamUser.objects.get(valveID=add_user)
        userStats = models.UserHeroStats.objects.get(user=user,hero=hero)

        if userStats.games > 20:
            userWinRate = 1.*userStats.win / userStats.games
        else:
            userWinRate = 0.

        print('{} on {}, win rate {}'.format(user, hero, userWinRate))

        if 'team_n_public' in feature_list:
            featureDict['RADIANT']['team_n_public'] += 1

        if 'team_average_ngames_hero' in feature_list:
            newAverage = 4.*featureDict['RADIANT']['team_average_ngames_hero']
            newAverage += userStats.games
            newAverage /= 5.
            featureDict['RADIANT']['team_average_ngames_hero'] = newAverage

        if 'team_average_win_rate_hero' in feature_list:
            newAverage = 4.*featureDict['RADIANT']['team_average_win_rate_hero']
            newAverage += userWinRate
            newAverage /= 5.
            featureDict['RADIANT']['team_average_win_rate_hero'] = newAverage

        ### Adjust the features that are team_top ###
        if ('team_top_n_games_hero' in feature_list and 
            userStats.games > featureDict['RADIANT']['team_top_n_games_hero']):
            featureDict['RADIANT']['team_top_n_games_hero'] = userStats.games

        if ('team_top_meta_win_rate' in feature_list and 
            hero.metaWinRate > featureDict['RADIANT']['team_top_meta_win_rate']):
            featureDict['RADIANT']['team_top_meta_win_rate'] = hero.metaWinRate

    return featureDict



def compute_features(heroDraftDict,userDraftDict,feature_list=[]):

    # initialize all lists and key,values

    allHeroRoles = models.HeroRoles.objects.all()
    allHeros = models.Hero.objects.all()

    radiant_features = OrderedDict()
    dire_features = OrderedDict()
    featureDict = OrderedDict()

    for key in feature_list:
        radiant_features[key] = 0
        dire_features[key] = 0

    featureDict['RADIANT'] = radiant_features
    featureDict['DIRE'] = dire_features

    for side in ['RADIANT','DIRE']:

        # init team based metrics
        team_n_public = 0

        player_ngames_hero_list = []
        player_ngames_with_hero_list = []
        player_ngames_against_hero_list = []

        player_winrate_hero_list = []
        player_winrate_with_hero_list = []
        player_winrate_against_hero_list = []
        player_hero_sentiment_list = []
        player_hero_meta_winrate_list = []

        for userKey,account_id in userDraftDict.items():

            # process one team at a time
            procDireSide = (side == 'DIRE' and 'enemySlot' in userKey)
            procRadiantSide = (side == 'RADIANT' and 'myTeamSlot' in userKey)

            if procRadiantSide or procDireSide:

                heroKey = userKey.replace('_user','_hero')

                # don't add the user's hero on the first pass through,
                # otherwise the roles etc will get double counted
                if heroKey == 'myTeamSlot1_hero':
                    pdb.set_trace()
                    continue

                hero = heroDraftDict[heroKey]
                roles = hero.roles.all()
                abilities = hero.abilities.all()

                player_hero_sentiment_list.append(hero.chatSentiment)
                player_hero_meta_winrate_list.append(hero.metaWinRate)

                # assemble behavior list for this hero
                behaviorList = []
                for ability in abilities:
                    for behavior in ability.behavior.all():
                        behaviorList.append(behavior.behavior.lower().replace(' ','_'))

                # capture role and ability behavior features
                for feature in feature_list:

                    # loop over roles, add role-based features
                    for role in roles:
                        if '_'.join(feature.split('_')[1:]).lower() == role.role.lower():
                            try:
                                featureDict[side][feature] += 1
                            except KeyError:
                                logger.error('Key {} not in featureDict'.format(feature))

                    # now loop over abilities, add ability-based features
                    for behavior in behaviorList:
                        if '_'.join(feature.split('_')[1:]).lower() == behavior.lower():
                            featureDict[side][feature] += 1

                # now add the SteamUser player-based features
                ## 1. retrieve player rank and ngames with hero
                if account_id != '':
                    team_n_public += 1

                    userInstance = models.SteamUser.objects.get(valveID=account_id)

                    # check if the user has stats in our DB
                    if models.UserHeroStats.objects.filter(user=userInstance).exists():
                        logger.info('FOUND USER {} IN THE DATABSE!'.format(userInstance.valveID))
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
                    else:

                        logger.info('QUERYING OD FOR PLAYER STATS')

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

                        # now get this hero's stats for further processing
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
                            logger.error(e)
                            heroStatsList = []

                # no public profile, just default to pro stats
                else:
                    logger.info('NO USER INFO, DEFAULTING TO THE META, ASSUMING 100 GAMES')
                    heroStatsList = [{
                        'hero_id': hero.valveID,
                        'games': 100,
                        'win': int(100*hero.metaWinRate),
                        'with_games': 0,
                        'with_win': 0,
                        'against_games': 0,
                        'against_win': 0,
                    }]

                # now total stuff up
                playerNGames = 0
                playerNGames_with = 0
                playerNGames_against = 0
                playerWinrate = 0
                playerWinrate_with = 0
                playerWinrate_against = 0

                # this should be a one element list
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

                player_winrate_hero_list.append(playerWinrate)
                player_winrate_with_hero_list.append(playerWinrate_with)

            ## 3.compute team stats, add to feature dict
            if len(player_ngames_hero_list) == 0:
                player_ngames_hero_list = [0.]
            if len(player_ngames_with_hero_list) == 0:
                player_ngames_with_hero_list = [0.]
            if len(player_winrate_hero_list) == 0:
                player_winrate_hero_list = [0.]
            if len(player_winrate_with_hero_list) == 0:
                player_winrate_with_hero_list = [0.]
            if len(player_hero_sentiment_list) == 0:
                player_hero_sentiment_list = [0.]
            if len(player_hero_meta_winrate_list) == 0:
                player_hero_meta_winrate_list = [0.]

            team_top_n_games_hero = np.array(player_ngames_hero_list).max()
            team_top_n_games_with_hero = np.array(player_ngames_with_hero_list).max()
            team_top_win_rate_hero = np.array(player_winrate_hero_list).max()
            team_top_win_rate_with_hero = np.array(player_winrate_with_hero_list).max()
            team_top_meta_win_rate = np.array(player_hero_meta_winrate_list).max()

            team_average_ngames_hero = np.array(player_ngames_hero_list).mean()
            team_average_ngames_with_hero = np.array(player_ngames_with_hero_list).mean()
            team_average_win_rate_hero = np.array(player_winrate_hero_list).mean()
            team_average_win_rate_with_hero = np.array(player_winrate_with_hero_list).mean()
            team_average_meta_win_rate = np.array(player_hero_meta_winrate_list).mean()
            team_average_sentiment = np.array(player_hero_sentiment_list).mean()

            team_stat_feature_dict = {
                    'team_n_public': team_n_public,

                    'team_top_n_games_hero': team_top_n_games_hero,
                    'team_top_n_games_with_hero': team_top_n_games_with_hero,
                    'team_top_win_rate_hero': team_top_win_rate_hero,
                    'team_top_win_rate_with_hero': team_top_win_rate_with_hero,
                    'team_top_meta_win_rate': team_top_meta_win_rate,

                    'team_average_ngames_hero': team_average_ngames_hero,
                    'team_average_ngames_with_hero': team_average_ngames_with_hero,
                    'team_average_win_rate_hero': team_average_win_rate_hero,
                    'team_average_win_rate_with_hero': team_average_win_rate_with_hero,
                    'team_average_win_rate_hero': team_average_win_rate_hero,
                    'team_average_meta_win_rate': team_average_meta_win_rate,
                }

            # dump the team stats into the featureDict
            for feature,statValue in team_stat_feature_dict.items():
                if feature in feature_list:
                    featureDict[side][feature] = statValue

            # chat sentiment
            featureDict[side]['chat_sentiment'] = team_average_sentiment

    # return
    return featureDict

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
    elif queryRes.status_code == 429:
        print('OOPS, RATE LIMIT EXCEEDED')
        time.sleep(0.05)
        return getHeroStats(account_id)
    else:
        return []


def map(request):

    map_options = GMapOptions(lat=30.2861, lng=-97.7394, map_type="roadmap", zoom=11)
    # init scatter plot
    api_key = settings.GOOGLE_API_KEY
    bokehAx = bp.gmap(api_key, map_options, title="Austin")

    source = ColumnDataSource(
        data={
            'lat':[ 30.29,  30.20,  30.29],
            'lon':[-97.70, -97.74, -97.78]
        }
    )

    bokehAx.circle(x="lon", y="lat", size=15, fill_color="blue", fill_alpha=0.8, source=source)

    # labels etc
    #bokehAx.title.text = ''
    #bokehAx.xaxis.axis_label = 'lat'
    #bokehAx.yaxis.axis_label = 'lon'
    plotResponse = file_html(bokehAx,CDN,'map')

    return HttpResponse(plotResponse)



