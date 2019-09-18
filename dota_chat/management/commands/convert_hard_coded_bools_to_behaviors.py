import sys, os, pdb, json,random
import urllib.request
from django.core.management.base import BaseCommand, CommandError
import dota_chat.models as models

class Command(BaseCommand):
    help = 'Converts the errant hard coded abilities to behavior M2M'

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

        verbose = options.get('verbose')

        try:
            ability_list = models.HeroAbility.objects.all()

            # for each ability, get the hard coded things and
            # if true, add them as a many to many to behaviors
            for ability in ability_list:
                if ability.isChannelCancelling:
                    behavior = models.AbilityBehaviors.objects.get(behavior='Channel Cancelling')
                    ability.behavior.add(behavior)

                if ability.isHardDisable:
                    behavior = models.AbilityBehaviors.objects.get(behavior='Hard Disable')
                    ability.behavior.add(behavior)

                if ability.isDisable:
                    behavior = models.AbilityBehaviors.objects.get(behavior='Disable')
                    ability.behavior.add(behavior)

                if ability.isChanneled:
                    behavior = models.AbilityBehaviors.objects.get(behavior='Channeled')
                    ability.behavior.add(behavior)

                if ability.isCoreSpell:
                    behavior = models.AbilityBehaviors.objects.get(behavior='Core Spell')
                    ability.behavior.add(behavior)

                if ability.isAghsSpell:
                    behavior = models.AbilityBehaviors.objects.get(behavior='Granted By Scepter')
                    ability.behavior.add(behavior)

                if ability.isTalent:
                    behavior = models.AbilityBehaviors.objects.get(behavior='Talent')
                    ability.behavior.add(behavior)

                ability.save()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed on: {}'.format(str(e))))
