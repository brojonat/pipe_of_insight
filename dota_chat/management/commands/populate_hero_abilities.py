import sys, os, pdb, json
import urllib.request
from django.core.management.base import BaseCommand, CommandError
import dota_chat.models as models

class Command(BaseCommand):
    help = 'Populates hero abilities from dotaconstants JSON file(s)'

    def add_arguments(self, parser):
        # required args
        parser.add_argument('--verbose', action='store_true')
        # Named (optional) arguments
        # parser.add_argument(
        #     '--delete',
        #     action='store_true',
        #     help='Delete poll instead of closing it',
        # )
        pass

    def handle(self, *args, **options):

        try:

            # grab the hero_abilities file
            if not options.get('infile'):
                infile = 'https://raw.githubusercontent.com/brojonat/dotaconstants/master/build/hero_abilities.json'
            else:
                infile = options.get('infile')

            if 'http' in infile:
                response = urllib.request.urlopen(infile)
                heroAbilityDataDict = json.loads(response.read())

        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to fetch data: {}'.format(str(e))))
            pdb.set_trace()

        # loop over the hero abilities
        for dotaHeroName,abilityDict in heroAbilityDataDict.items():

            # extract abilities/talents
            abilities = abilityDict['abilities']
            talents = abilityDict['talents']

            # grab relevant hero
            hero = models.Hero.objects.get(valveName=dotaHeroName)

            # clear all current abilities
            hero.abilities.clear()

            # store abilities in the hero model
            try:
                # assign talents
                abilitySlot = 0
                for abilityStr in abilities:
                    abilitySlot += 1

                    # fetch the ability
                    ability = models.HeroAbility.objects.get(abilityName=abilityStr)

                    # modify/add our custom features
                    ability.abilitySlot = abilitySlot

                    if abilityStr != 'generic_hidden':
                        ability.isCoreSpell = True

                    ability.save()

                    # add it to the m2m
                    hero.abilities.add(ability)

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR('Failed to store ability: {}'.format(str(e))))
                pdb.set_trace()

            # store talents in the hero model
            try:
                talentSlot = 0
                for talentDict in talents:
                    talentSlot += 1

                    talentStr = talentDict['name']

                    # we store talents like abilities
                    ability = models.HeroAbility.objects.get(abilityName=talentStr)

                    # modify/add our custom features
                    ability.abilitySlot = talentSlot
                    ability.isTalent = True

                    ability.save()

                    # add it to the m2m
                    hero.abilities.add(ability)

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR('Failed to store talent: {}'.format(str(e))))
                pdb.set_trace()

            self.stdout.write(
                self.style.SUCCESS('Added abilities to: {}'.format(str(hero))))
