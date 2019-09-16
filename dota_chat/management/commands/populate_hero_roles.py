import sys, os, pdb, json
import urllib.request
from django.core.management.base import BaseCommand, CommandError
import dota_chat.models as models

class Command(BaseCommand):
    help = 'Populates hero models from dotaconstants JSON file'

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
            roles_list = models.HeroRoles.role_choices

            for role_tuple in roles_list:
                created,instance = models.HeroRoles.objects.get_or_create(role=role_tuple[0])


        except Exception as e:
            self.stdout.write(
                self.style.ERROR('Failed to create roles: {}'.format(str(e))))
