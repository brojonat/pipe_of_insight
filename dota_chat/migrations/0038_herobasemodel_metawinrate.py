# Generated by Django 2.1.5 on 2019-09-26 19:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dota_chat', '0037_herobasemodel_chatsentiment'),
    ]

    operations = [
        migrations.AddField(
            model_name='herobasemodel',
            name='metaWinRate',
            field=models.FloatField(default=0.0),
        ),
    ]