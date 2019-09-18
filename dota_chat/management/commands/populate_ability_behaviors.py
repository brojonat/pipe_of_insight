import sys, os, pdb, json,random
import urllib.request
from django.core.management.base import BaseCommand, CommandError
import dota_chat.models as models

class Command(BaseCommand):
    help = 'Populates ability behaviors from dotaconstants JSON file'

    def add_arguments(self, parser):
        # required args
        parser.add_argument('--verbose', action='store_true')
        parser.add_argument('--all-new-colors', action='store_true',
                            help='New colors for ALL behaviors')
        parser.add_argument('--limited-new-colors', action='store_true',
                            help='Limit new colors to only newly created behaviors')

        # Named (optional) arguments
        # parser.add_argument(
        #     '--delete',
        #     action='store_true',
        #     help='Delete poll instead of closing it',
        # )
        pass

    def handle(self, *args, **options):

        verbose = options.get('verbose')
        all_new_colors = options.get('all_new_colors')
        limited_new_colors = options.get('limited_new_colors')

        try:
            behavior_list = models.AbilityBehaviors.behavior_choices

            for behavior_tuple in behavior_list:
                behaviorInstance,behaviorCreated = models.AbilityBehaviors.objects.get_or_create(behavior=behavior_tuple[0])

                if all_new_colors or (limited_new_colors and behaviorCreated):
                    random_number = random.randint(0,16777215)
                    hex_number = str(hex(random_number))
                    hex_number ='#'+ hex_number[2:]

                    colorInstance,colorCreated = models.AbilityBehaviorColors.objects.get_or_create(colorHex=hex_number)
                    behaviorInstance.color = colorInstance

                    if verbose:
                        outStr = '{} has color {}'.format(behaviorInstance, hex_number)
                        self.stdout.write(self.style.SUCCESS(outStr))


                behaviorInstance.save()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to create behavior: {}'.format(str(e))))
