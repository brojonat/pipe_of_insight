# Generated by Django 2.1.5 on 2019-08-30 00:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='HeroBaseModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valveID', models.IntegerField(unique=True)),
                ('valveName', models.CharField(max_length=50, unique=True)),
                ('name', models.CharField(max_length=50, unique=True)),
                ('primary_attr', models.CharField(choices=[('agi', 'agility'), ('str', 'strength'), ('int', 'intelligence')], max_length=3)),
                ('attack_type', models.CharField(choices=[('Melee', 'Melee'), ('Ranged', 'Ranged')], max_length=10)),
                ('opendota_img', models.CharField(max_length=100)),
                ('opendota_icon', models.CharField(max_length=100)),
                ('base_health', models.IntegerField()),
                ('base_health_regen', models.IntegerField()),
                ('base_mana', models.FloatField()),
                ('base_mana_regen', models.FloatField()),
                ('base_armor', models.IntegerField()),
                ('base_mr', models.IntegerField()),
                ('base_attack_min', models.IntegerField()),
                ('base_attack_max', models.IntegerField()),
                ('base_str', models.IntegerField()),
                ('base_agi', models.IntegerField()),
                ('base_int', models.IntegerField()),
                ('str_gain', models.FloatField()),
                ('agi_gain', models.FloatField()),
                ('int_gain', models.FloatField()),
                ('attack_range', models.IntegerField()),
                ('projectile_speed', models.IntegerField()),
                ('attack_rate', models.FloatField()),
                ('move_speed', models.IntegerField()),
                ('turn_rate', models.FloatField()),
                ('cm_enabled', models.BooleanField()),
                ('legs', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='HeroRoles',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('Carry', 'Carry'), ('Suppor', 'Support'), ('Pusher', 'Pusher'), ('Jungler', 'Jungler'), ('Disabler', 'Disabler'), ('Initiator', 'Initiator'), ('Escape', 'Escape'), ('Durable', 'Durable'), ('Nuker', 'Nuker')], max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('matchID', models.IntegerField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='SteamUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valveID', models.IntegerField(unique=True)),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Hero',
            fields=[
                ('herobasemodel_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='dota_chat.HeroBaseModel')),
                ('slug', models.SlugField(unique=True)),
                ('img', models.ImageField(upload_to='')),
                ('icon', models.ImageField(upload_to='')),
            ],
            bases=('dota_chat.herobasemodel',),
        ),
        migrations.AddField(
            model_name='herobasemodel',
            name='roles',
            field=models.ManyToManyField(to='dota_chat.HeroRoles'),
        ),
    ]
