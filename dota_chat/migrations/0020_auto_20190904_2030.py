# Generated by Django 2.1.5 on 2019-09-04 20:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dota_chat', '0019_player_wonmatch'),
    ]

    operations = [
        migrations.AddField(
            model_name='heroability',
            name='isAghsSpell',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='heroability',
            name='isCoreSpell',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='heroability',
            name='isTalent',
            field=models.BooleanField(default=False),
        ),
    ]
