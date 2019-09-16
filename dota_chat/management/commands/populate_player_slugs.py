import sys, os, pdb
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
import dota_chat.models as models



class Command(BaseCommand):
    help = 'Populates Player slug fields'

    def add_arguments(self, parser):
        # required args
        # Named (optional) arguments
        # parser.add_argument(
        #     '--delete',
        #     action='store_true',
        #     help='Delete poll instead of closing it',
        # )
        pass

    def handle(self, *args, **options):


        # slugify Players
        players = models.Player.objects.all()
        for player in players:
            try:
                # locate the poorly ID'd Target
                player.save()
                successStr = 'Successfully slugged target {}'.format(player)
                self.stdout.write(self.style.SUCCESS(successStr))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR('Failed to slug {}: {}'.format(player,str(e))))

