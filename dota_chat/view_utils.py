import os,sys,shutil,pdb,glob,logging,datetime,time,json,random
import numpy as np 
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




def winRatePlot(request,hero_id,USE_PRO=True):

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
    bokehAx.xaxis.axis_label = 'wins'
    bokehAx.yaxis.axis_label = 'losses'
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
    allMatches = models.Match.objects.all()
    startTimes = [match.start_time for match in allMatches]
    durationTimes = [match.duration/60. for match in allMatches]

    # Start times
    hist, edges = np.histogram(startTimes, density=False, bins=50)
    x = np.linspace(np.min(startTimes),np.max(startTimes),1000)
    p1 = make_histogram_plot_only(
                'Match Start', hist, edges,
                xlabel='some arbitrary offset',
                ylabel='Relative Count')

    # Duration times
    hist, edges = np.histogram(durationTimes, density=False, bins=50)
    x = np.linspace(np.min(durationTimes),np.max(durationTimes),1000)
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



