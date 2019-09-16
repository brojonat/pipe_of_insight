import sys, os, pdb, json
import urllib.request
from django.core.management.base import BaseCommand, CommandError
import dota_chat.models as models

class Command(BaseCommand):
    help = 'Populates ability behaviors from dotaconstants JSON file'

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
            behavior_list = models.AbilityBehaviors.behavior_choices

            for behavior_tuple in behavior_list:
                created,instance = models.AbilityBehaviors.objects.get_or_create(behavior=behavior_tuple[0])


        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to create behavior: {}'.format(str(e))))
