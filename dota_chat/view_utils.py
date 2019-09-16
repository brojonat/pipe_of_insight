import os,sys,shutil,pdb,glob,logging,datetime,time,json
import numpy as np 

import requests

from . import models as models

from django.conf import settings
from django.http import HttpResponse, JsonResponse 
from django.http import HttpResponseRedirect, HttpResponseServerError, HttpResponseForbidden
from django.urls import reverse
from django.urls import reverse, reverse_lazy

import bokeh.plotting as bp
from bokeh.resources import CDN
from bokeh.embed import file_html
from bokeh.models import ColumnDataSource,Range1d,Span,LinearAxis,Label,Title,HoverTool,GMapOptions
from bokeh.models.markers import Circle
from bokeh.models.glyphs import ImageURL
from bokeh.core.properties import FontSizeSpec

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
        pdb.set_trace()

    dataDict = queryRes.json()

    # passively prevent rate exceeding if many queries
    time.sleep(kwargs.get('sleepTime',0.05)) 

    return dataDict




def winRatePlot(request,hero_id):

    # assemble data
    heroInstance = models.Hero.objects.get(valveID=hero_id)
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

    wlRates = [wins/(wins+losses),losses/(wins+losses)]

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

