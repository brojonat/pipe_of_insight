# Generated by Django 2.1.5 on 2019-09-17 18:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dota_chat', '0029_auto_20190917_1856'),
    ]

    operations = [
        migrations.AlterField(
            model_name='abilitybehaviorcolors',
            name='colorHex',
            field=models.CharField(max_length=10, unique=True),
        ),
    ]
