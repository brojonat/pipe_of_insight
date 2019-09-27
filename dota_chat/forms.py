import os,pdb,sys

from . import models as models

from django import forms

class DraftForm(forms.Form):

    def __init__(self,*args,**kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ''  # Removes : as label suffix

    allHeros = models.Hero.objects.all().order_by('slug')

    nullChoiceList = [('','(Empty)')]
    heroChioces = [(h.valveID,h.prettyName) for h in allHeros]
    heroChioces = nullChoiceList+heroChioces

    myTeamSlot1_hero = forms.ChoiceField(required=False,choices=heroChioces,label = 'Your Hero (optional):')
    myTeamSlot2_hero = forms.ChoiceField(required=False,choices=heroChioces,label = 'Allied Hero:')
    myTeamSlot3_hero = forms.ChoiceField(required=False,choices=heroChioces,label = 'Allied Hero:')
    myTeamSlot4_hero = forms.ChoiceField(required=False,choices=heroChioces,label = 'Allied Hero:')
    myTeamSlot5_hero = forms.ChoiceField(required=False,choices=heroChioces,label = 'Allied Hero:')

    myTeamSlot1_user = forms.CharField(required=False,widget=forms.TextInput(attrs={'class':'form-control','id':'allySearch_1'}),label = 'Your Steam Name')
    myTeamSlot2_user = forms.CharField(required=False,widget=forms.TextInput(attrs={'class':'form-control','id':'allySearch_2'}),label = 'Steam User')
    myTeamSlot3_user = forms.CharField(required=False,widget=forms.TextInput(attrs={'class':'form-control','id':'allySearch_3'}),label = 'Steam User')
    myTeamSlot4_user = forms.CharField(required=False,widget=forms.TextInput(attrs={'class':'form-control','id':'allySearch_4'}),label = 'Steam User')
    myTeamSlot5_user = forms.CharField(required=False,widget=forms.TextInput(attrs={'class':'form-control','id':'allySearch_5'}),label = 'Steam User')

    enemySlot1_hero = forms.ChoiceField(required=False,choices=heroChioces,label = 'Enemy Hero:')
    enemySlot2_hero = forms.ChoiceField(required=False,choices=heroChioces,label = 'Enemy Hero:')
    enemySlot3_hero = forms.ChoiceField(required=False,choices=heroChioces,label = 'Enemy Hero:')
    enemySlot4_hero = forms.ChoiceField(required=False,choices=heroChioces,label = 'Enemy Hero:')
    enemySlot5_hero = forms.ChoiceField(required=False,choices=heroChioces,label = 'Enemy Hero:')

    enemySlot1_user = forms.CharField(required=False,widget=forms.TextInput(attrs={'class':'form-control','id':'enemySearch_1'}),label = 'Steam User')
    enemySlot2_user = forms.CharField(required=False,widget=forms.TextInput(attrs={'class':'form-control','id':'enemySearch_2'}),label = 'Steam User')
    enemySlot3_user = forms.CharField(required=False,widget=forms.TextInput(attrs={'class':'form-control','id':'enemySearch_3'}),label = 'Steam User')
    enemySlot4_user = forms.CharField(required=False,widget=forms.TextInput(attrs={'class':'form-control','id':'enemySearch_4'}),label = 'Steam User')
    enemySlot5_user = forms.CharField(required=False,widget=forms.TextInput(attrs={'class':'form-control','id':'enemySearch_5'}),label = 'Steam User')


    def assess_draft(self):
        # send email using the self.cleaned_data dictionary
        pass
