# Generated by Django 2.1.5 on 2019-08-30 19:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dota_chat', '0009_auto_20190830_1924'),
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valveID', models.IntegerField(unique=True)),
                ('opendota_img', models.CharField(max_length=100, null=True)),
                ('dname', models.CharField(max_length=100, unique=True)),
                ('cost', models.IntegerField()),
                ('notes', models.TextField(null=True)),
                ('manaCost', models.FloatField(null=True)),
                ('cooldown', models.FloatField(null=True)),
                ('lore', models.TextField(null=True)),
                ('slug', models.SlugField(unique=True)),
            ],
            options={
                'verbose_name_plural': 'Items',
            },
        ),
    ]
