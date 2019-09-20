"""spec_browser URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path, include

from . import views
from . import view_utils as view_utils

from django.contrib.auth import views as auth_views


urlpatterns = [
    # home
    re_path(r'^$', views.index, name='index'),
    re_path(r'^login/$', auth_views.LoginView.as_view(template_name='dota_chat/login.html'),name='auth_login'),
    re_path(r'^logout/$', auth_views.LogoutView.as_view(template_name='dota_chat/logged_out.html'), name='auth_logout'),
    re_path(r'^dashboard/$', views.dashboard, name='dashboard'),
    
    re_path(r'^heroes/$',views.HeroListView.as_view(),name='hero_list_view'),
    re_path(r'^heroes/(?P<slug>[\w-]+)/$',views.HeroDetailView.as_view(),name='hero_detail_view'),

    re_path(r'abilities/$',views.AbilityListView.as_view(),name='ability_list_view'),
    re_path(r'abilities/(?P<pk>[0-9]+)/$',views.AbilityDetailView.as_view(),name='ability_detail_view'),

    re_path(r'^players/$',views.PlayerListView.as_view(),name='player_list_view'),
    re_path(r'^players/(?P<slug>[\w-]+)/$',views.PlayerDetailView.as_view(),name='player_detail_view'),

    re_path(r'^users/$',views.UserListView.as_view(),name='user_list_view'),
    re_path(r'^users/(?P<pk>[0-9]+)/$',views.UserDetailView.as_view(),name='user_detail_view'),


]

urlpatterns_functions = [
    re_path(r'^winRatePlot/(?P<hero_id>[0-9]+)/$', view_utils.winRatePlot, name='win_rate_plot'),
    re_path(r'^winLossChatPlot/(?P<hero_id>[0-9]+)/$', view_utils.winLossChatPlot, name='win_loss_chat_plot'),
    re_path(r'^map/$', view_utils.map, name='map'),
    re_path(r'^temporal_histograms/$', view_utils.temporal_histograms, name='temporal_histograms'),
    re_path(r'^hero_popularity_histogram/$', view_utils.hero_popularity_histogram, name='hero_popularity_histogram'),
    re_path(r'^region_histogram/$', view_utils.region_histogram, name='region_histogram'),

]

urlpattern_lists = [
    re_path(r'^addAbilityBehaviors/$', views.addAbilityBehaviors, name='add_ability_behaviors'),
    re_path(r'^removeAbilityBehaviors/$', views.removeAbilityBehaviors, name='remove_ability_behaviors'),
    re_path(r'^dynamic_user_search/', views.dynamic_user_search,name='dynamic_user_search'),
    re_path(r'^user_search_redirect/', views.user_search_redirect,name='user_search_redirect'),

]

urlpatterns += urlpatterns_functions
urlpatterns += urlpattern_lists