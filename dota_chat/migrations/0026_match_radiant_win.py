# Generated by Django 2.1.5 on 2019-09-16 05:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dota_chat', '0025_auto_20190911_2336'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='radiant_win',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]
