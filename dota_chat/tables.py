import os,pdb,datetime
from django.db.models import Q, F, Sum
from django.contrib.auth.models import User
from . import models as models
import django_tables2 as tables

from django.utils.safestring import mark_safe
from django.utils.html import escape

class ImageColumn(tables.Column):
    def render(self, value):
        return mark_safe('<img src="{}" />'.format(escape(value)))


class HeroListTable(tables.Table):
    heroIcon = ImageColumn(accessor='icon.url',
                                  linkify=('hero_detail_view', {'slug': tables.A('slug')}),
                                  verbose_name='',
                                  attrs={"td": {"width": 50}})
    heroLink = tables.Column(accessor='prettyName',
                             linkify=('hero_detail_view', {'slug': tables.A('slug')}),
                             verbose_name='')


    class Meta:
        model = models.Hero
        template_name = 'django_tables2/bootstrap4.html'
        fields = ['heroIcon','heroLink']

class PlayerListTable(tables.Table):
    heroIcon = ImageColumn(accessor='hero.icon.url',
                           linkify=('player_detail_view', {'slug': tables.A('slug')}),
                           verbose_name='',
                           attrs={"td": {"width": 50}})
    playerLink = tables.Column(accessor='name',
                             linkify=('player_detail_view', {'slug': tables.A('slug')}),
                             verbose_name='')

    class Meta:
        model = models.Player
        template_name = 'django_tables2/bootstrap4.html'
        fields = ['heroIcon','playerLink']

class UserListTable(tables.Table):
    userLink = tables.Column(accessor='name',
                             linkify=('user_detail_view', {'pk': tables.A('pk')}),
                             verbose_name='Steam User')

    class Meta:
        model = models.SteamUser
        template_name = 'django_tables2/bootstrap4.html'
        fields = ['userLink']