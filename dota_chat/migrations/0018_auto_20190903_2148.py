# Generated by Django 2.1.5 on 2019-09-03 21:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dota_chat', '0017_auto_20190903_2142'),
    ]

    operations = [
        migrations.AlterField(
            model_name='match',
            name='matchID',
            field=models.BigIntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name='steamuser',
            name='valveID',
            field=models.BigIntegerField(unique=True),
        ),
    ]
