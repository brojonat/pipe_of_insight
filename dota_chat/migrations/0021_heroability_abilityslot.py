# Generated by Django 2.1.5 on 2019-09-04 21:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dota_chat', '0020_auto_20190904_2030'),
    ]

    operations = [
        migrations.AddField(
            model_name='heroability',
            name='abilitySlot',
            field=models.IntegerField(null=True),
        ),
    ]
