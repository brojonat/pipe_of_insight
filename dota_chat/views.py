import os,sys,shutil,pdb,glob,logging,datetime,tarfile,json,copy
import numpy as np 

from . import models as models
from . import tables as tables
from . import view_utils as view_utils

from django.conf import settings
from django.db.models import Q, F, Avg

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import HttpResponse, JsonResponse 
from django.http import HttpResponseRedirect, HttpResponseServerError, HttpResponseForbidden

from django.urls import reverse
from django.urls import reverse, reverse_lazy

from django.utils import timezone
from django.utils.encoding import smart_str

from django.views.generic import View, ListView, DetailView
from django.views.generic import UpdateView, DeleteView, CreateView
from django.views.generic.base import ContextMixin
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from django.shortcuts import render,redirect,get_object_or_404

from django_tables2 import RequestConfig

# Create your views here.

class HeroListView(ListView):
    ''' ListView for heros in Dota 2 '''
    model = models.Hero 
    template_name = 'dota_chat/hero/hero_list_view.html'
    context_object_name = 'viewContent'

    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user.username

        table = tables.HeroListTable(models.Hero.objects.all().order_by('name'))
        RequestConfig(self.request,paginate={'per_page':15}).configure(table)
        context['table'] = table

        return {self.context_object_name: context}


class HeroDetailView(DetailView):
    ''' DetailView for heros in Dota 2 '''
    model = models.Hero
    template_name = 'dota_chat/hero/hero_detail_view.html'
    context_object_name = 'viewContent'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user.username

        # construct abilities
        allAbilities = list(self.object.abilities.all().order_by('abilitySlot'))
        allAbilityBehaviors = list(models.AbilityBehaviors.objects.all().order_by('behavior'))

        abilities = []

        for ability in allAbilities:
            isCoreSpell = ability.behavior.filter(behavior='Core Spell').exists()
            isAghsSpell = ability.behavior.filter(behavior='Granted By Scepter').exists()
            isHidden = ability.behavior.filter(behavior='Hidden').exists()

            if ability.img and (isCoreSpell or isAghsSpell) and not isHidden:
                abilities.append(ability)

        context['abilities'] = abilities

        # construct chat
        chatLog = {}
        allPlayers = list(self.object.player_set.all())
        #allPlayers = []
        for player in allPlayers:
            playerName = player.name
            allChat = player.chatentry_set.all()
            for chat in allChat:
                entry = (chat.chatTime,chat.chatText)
                if playerName in chatLog.keys():
                    chatLog[playerName].append(entry)
                else:
                    chatLog[playerName] = [entry]
        context['chat'] = chatLog

        context['allAbilityBehaviors'] = []
        context['allBehaviorColors'] = []

        for abilityBehavior in allAbilityBehaviors:
            context['allAbilityBehaviors'].append(abilityBehavior)
            context['allBehaviorColors'].append(abilityBehavior.color)

        return {self.context_object_name: context}


class AbilityListView(ListView):
    ''' ListView for abilities in Dota 2 '''
    model = models.HeroAbility 
    template_name = 'dota_chat/hero/ability_list_view.html'
    context_object_name = 'viewContent'

    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user.username

        table = tables.AbilityListTable(models.HeroAbility.objects.all().order_by('name'))
        RequestConfig(self.request,paginate={'per_page':50}).configure(table)
        context['table'] = table

        return {self.context_object_name: context}


class AbilityDetailView(DetailView):
    ''' DetailView for abilities in Dota 2 '''
    model = models.HeroAbility
    template_name = 'dota_chat/hero/ability_detail_view.html'
    context_object_name = 'viewContent'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user.username
        return {self.context_object_name: context}

class PlayerListView(ListView):
    ''' List view for all players '''
    model = models.Player 
    template_name = 'dota_chat/player/player_list_view.html'
    context_object_name = 'viewContent'

    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)

        table = tables.PlayerListTable(models.Player.objects.all().order_by('name'))
        RequestConfig(self.request,paginate={'per_page':15}).configure(table)
        context['table'] = table

        return {self.context_object_name: context}

class PlayerDetailView(DetailView):
    ''' DetailView for players '''
    model = models.Player
    template_name = 'dota_chat/player/player_detail_view.html'
    context_object_name = 'viewContent'

    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user.username

        # construct chat
        chatLog = {}
        #allPlayers = list(self.object.player_set.all())
        playerName = self.object.name
        allChat = self.object.chatentry_set.all()
        for chat in allChat:
            entry = (chat.chatTime,chat.chatText)
            if playerName in chatLog.keys():
                chatLog[playerName].append(entry)
            else:
                chatLog[playerName] = [entry]
        context['chat'] = chatLog

        return {self.context_object_name: context}


class UserListView(ListView):
    ''' ListView for Steam users '''
    model = models.SteamUser
    template_name = 'dota_chat/user/user_list_view.html'
    context_object_name = 'viewContent'

    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)

        table = tables.UserListTable(models.SteamUser.objects.all().order_by('name'))
        RequestConfig(self.request,paginate={'per_page':15}).configure(table)
        context['table'] = table

        return {self.context_object_name: context}


class UserDetailView(DetailView):
    ''' DetailView for players '''
    model = models.SteamUser
    template_name = 'dota_chat/user/user_detail_view.html'
    context_object_name = 'viewContent'

    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user.username

        # construct chat
        chatLog = {}
        userID = self.object.valveID
        allPlayers = self.object.player_set.all()
        for player in allPlayers:
            allChat = player.chatentry_set.all()

            for chat in allChat:
                entry = (chat.chatTime,chat.chatText)
                if player.slug in chatLog.keys():
                    chatLog[player.slug].append(entry)
                else:
                    chatLog[player.slug] = [entry]
        context['chat'] = chatLog

        return {self.context_object_name: context}






# auth/login/logout/index/dashboard and other function based views follow

def auth_login(request):
    ''' Login '''
    logout(request)
    next_page = request.POST.get('next')

    user = None
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        
        # Redirect to requested page
        if next_page:
            return HttpResponseRedirect(next_page)
        else:
            return HttpResponseRedirect(reverse('index'))
    else:
        return render(request, 'dota_chat/login.html')

def auth_logout(request):
    ''' Logout '''
    logout(request)
    return render(request, 'dota_chat/logout.html')


def index(request):
    ''' Handles proper redirections '''
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse_lazy('dashboard'))
    return render(request, 'dota_chat/index.html')

def dashboard(request):
    ''' Basic dashboard landing page '''
    viewContent = {}
    viewContent['testVariable'] = 'text'
    viewContent['user'] = request.user.username

    return render(request, 'dota_chat/basic.html', {'viewContent': viewContent})


def addAbilityBehaviors(request):
    if request.method == 'POST':
        abilityDict = json.loads(request.body)
        abilityID = abilityDict.get('abilityID')
        updatedBehaviorIDs = abilityDict.get('behaviorIDs')

        if abilityID is not None:
            ability = models.HeroAbility.objects.get(id=abilityID)
            currentBehaviors = ability.behavior.all()
            currentBehaviorIDs = [behavior.id for behavior in currentBehaviors]
        else:
            currentBehaviorIDs = []

        # add any that are in the current/updated list but not present
        for behaviorID in updatedBehaviorIDs:
            behavior = models.AbilityBehaviors.objects.get(id=behaviorID)
            ability.behavior.add(behavior)

        return JsonResponse({'success': True})

def removeAbilityBehaviors(request):
    if request.method == 'POST':
        abilityDict = json.loads(request.body)
        abilityID = abilityDict.get('abilityID')
        updatedBehaviorIDs = abilityDict.get('behaviorIDs')

        if abilityID is not None:
            ability = models.HeroAbility.objects.get(id=abilityID)
            currentBehaviors = ability.behavior.all()
            currentBehaviorIDs = [behavior.id for behavior in currentBehaviors]
        else:
            currentBehaviorIDs = []

        # add any that are in the current/updated list but not present
        for behaviorID in updatedBehaviorIDs:
            behavior = models.AbilityBehaviors.objects.get(id=behaviorID)
            ability.behavior.remove(behavior)



        return JsonResponse({'success': True})
