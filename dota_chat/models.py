import os, shutil
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.conf import settings


from django.utils.text import slugify


# Create your models here.

class HeroRoles(models.Model):
    ''' Static model for hero roles '''
    class Meta:
        verbose_name_plural = 'HeroRoles'

    # perhaps add some Features to roles?
    role_choices = ( ('Carry','Carry'),
                     ('Support','Support'),
                     ('Pusher','Pusher'),
                     ('Jungler','Jungler'),
                     ('Disabler','Disabler'),
                     ('Initiator','Initiator'),
                     ('Escape','Escape'),
                     ('Durable','Durable'),
                     ('Nuker','Nuker')
        )
    role = models.CharField(max_length=50,unique=True,choices=role_choices)

    def __str__(self):
        return str(self.role)

class AbilityBehaviorColors(models.Model):
    colorHex = models.CharField(max_length=10,unique=True)
    colorDescriptiveName = models.CharField(max_length=64,blank=True)
    def __str__(self):
        return self.colorHex

# not necessariliy complete, also need to populate
class AbilityBehaviors(models.Model):
    ''' Static model for ability behaviors '''
    class Meta:
        verbose_name_plural = 'AbilityBehaviors'

    # NOTE: some behaviors (Venge) have ['Passive',null]
    behavior_choices = ( ('Passive','Passive'),
                         ('No Target','No Target'),
                         ('Point Target','Point Target'),
                         ('Unit Target','Unit Target'),
                         ('AOE','AOE'),
                         ('Channeled','Channeled'),
                         ('Instant Cast','Instant Cast'),
                         ('Autocast','Autocast'),
                         ('Hidden','Hidden'),
                         ('Talent','Talent'),
                         ('Attack Modifier','Attack Modifier'),
                         ('Disable','Disable'),
                         ('Channel Cancelling','Channel Cancelling'),
                         ('Hard Disable','Hard Disable'),
                         ('Channeled','Channeled'),
                         ('Channeled Cast','Channeled Cast'),
                         ('Core Spell','Core Spell'),
                         ('Grants Self Physical Immunity','Grants Self Physical Immunity'),
                         ('Grants Self Magic Immunity','Grants Self Magic Immunity'),
                         ('Grants Ally Physical Immunity','Grants Ally Physical Immunity'),
                         ('Grants Ally Magic Immunity','Grants Ally Magic Immunity'),
                         ('Grants Enemy Physical Immunity','Grants Enemy Physical Immunity'),
                         ('Grants Enemy Magic Immunity','Grants Enemy Magic Immunity'),
                         ('Bash','Bash'),
                         ('Root','Root'),
                         ('Disarms Enemy','Disarms Enemy'),
                         ('Disarms Ally','Disarms Ally'),
                         ('Basic Dispel Self','Basic Dispel Self'),
                         ('Basic Dispel Ally','Basic Dispel Ally'),
                         ('Basic Dispel Enemy','Basic Dispel Enemy'),
                         ('Strong Dispel Self','Strong Dispel Self'),
                         ('Strong Dispel Ally','Strong Dispel Ally'),
                         ('Strong Dispel Enemy','Strong Dispel Enemy'),
                         ('Grants Invisibility','Grants Invisibility'),
                         ('Grants True Sight','Grants True Sight'),
                         ('Enhanced By Scepter','Enhanced By Scepter'),
                         ('Granted By Scepter','Granted By Scepter'),
                         ('Heals Teammates','Heals Teammates'),
                         ('AOE Denial','AOE Denial'),
                         ('Skill Shot','Skill Shot'),
                         ('Repositions Enemies','Repositions Enemies'),
                         ('Repositions Allies','Repositions Allies'),
                         ('Mutes','Mutes'),
                         ('Provides Miss Chance','Provides Miss Chance'),
                         ('Provides Armor', 'Provides Armor'),
                         ('Provides Armor Reduction', 'Provides Armor Reduction')
        )

    behavior = models.CharField(max_length=50,unique=True,choices=behavior_choices)
    color = models.ForeignKey(AbilityBehaviorColors, 
                                on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.behavior)


# not complete
class HeroAbilityBaseModel(models.Model):
    ''' Base class for static abilities '''
    damage_type_choices = ( ('Pure','Pure'),
                            ('Magical','Magical'),
                            ('Physical','Physical'),
                            (None,'null')
        )

    behavior = models.ManyToManyField(AbilityBehaviors)

    abilityName = models.CharField(max_length=100,unique=True)
    dname = models.CharField(max_length=100)
    dmg_type = models.CharField(max_length=50,choices=damage_type_choices,blank=True)
    bkbPierce = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    opendota_img = models.CharField(max_length=100,blank=True)
    manaCost = ArrayField(models.FloatField(null=True),null=True,blank=True)
    cooldown = ArrayField(models.FloatField(null=True),null=True,blank=True)

    def __str__(self):
        return str(self.dname)

# not complete
class HeroAbility(HeroAbilityBaseModel):
    ''' Static model for abilities '''
    class Meta:
        verbose_name_plural = 'HeroAbilities'

    abilitySlot = models.IntegerField(null=True,blank=True)
    img = models.ImageField(null=True,blank=True)

    @property
    def prettyName(self):
        name = self.dname.replace('-',' ').replace('_',' ')
        nameList = [s.capitalize() for s in name.split()]
        prettyName = ' '.join(nameList)
        return prettyName

    @property
    def ability_as_list(self):
        splitStr = self.description.split('\n')
        return splitStr

    @property
    def assignedBehaviors(self):
        return self.behavior.all().order_by('behavior')

    @property
    def availableBehaviors(self):
        availableBehaviors = list(AbilityBehaviors.objects.all().order_by('behavior'))
        assignedBehaviors = self.assignedBehaviors
        for behavior in assignedBehaviors:
            if behavior in availableBehaviors:
                availableBehaviors.remove(behavior)
        return availableBehaviors
    
    


class Item(models.Model):
    ''' Static model for dota items '''
    class Meta:
        verbose_name_plural = 'Items'
    itemName = models.CharField(max_length=100,unique=True)
    valveID = models.IntegerField(unique=True)
    opendota_img = models.CharField(max_length=100,blank=True)
    dname = models.CharField(max_length=100)
    cost = models.IntegerField()
    notes = models.TextField(blank=True)
    manaCost = models.FloatField(null=True,blank=True)
    cooldown = models.FloatField(null=True,blank=True)
    lore = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    img = models.ImageField(null=True,blank=True)


    def save(self, *args, **kwargs):
        self.slug = slugify(self.itemName)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.itemName)











class HeroBaseModel(models.Model):
    ''' Base class for static dota heros '''

    attr_choices = ( ('agi','agility'),
                     ('str','strength'),
                     ('int','intelligence')
        )
    attack_choices = ( ('Melee', 'Melee'),
                       ('Ranged', 'Ranged') 
        )

    roles = models.ManyToManyField(HeroRoles)

    valveID = models.IntegerField(unique=True) 
    valveName = models.CharField(max_length=50,unique=True)
    name = models.CharField(max_length=50,unique=True)
    primary_attr = models.CharField(max_length=3,choices=attr_choices)
    attack_type = models.CharField(max_length=10,choices=attack_choices)
    opendota_img = models.CharField(max_length=100,blank=True)
    opendota_icon = models.CharField(max_length=100,blank=True)
    base_health = models.IntegerField() 
    base_health_regen = models.IntegerField()
    base_mana = models.FloatField()
    base_mana_regen = models.FloatField()
    base_armor = models.IntegerField()
    base_mr = models.IntegerField()
    base_attack_min = models.IntegerField()
    base_attack_max = models.IntegerField()
    base_str = models.IntegerField()
    base_agi = models.IntegerField() 
    base_int = models.IntegerField()
    str_gain = models.FloatField()
    agi_gain = models.FloatField() 
    int_gain = models.FloatField()
    attack_range = models.IntegerField()
    projectile_speed = models.IntegerField()
    attack_rate = models.FloatField()
    move_speed = models.IntegerField()
    turn_rate = models.FloatField()
    cm_enabled = models.BooleanField()
    legs = models.IntegerField()

class Hero(HeroBaseModel):
    ''' Static model representing dota Heros '''

    abilities = models.ManyToManyField(HeroAbility)

    slug = models.SlugField(unique=True)
    img = models.ImageField(null=True,blank=True)
    icon = models.ImageField(null=True,blank=True)

    @property
    def shortName(self):
        shortName = self.slug.replace('-','')
        return shortName

    @property
    def prettyName(self):
        name = self.slug.replace('-',' ')
        nameList = [s.capitalize() for s in name.split()]
        prettyName = ' '.join(nameList)
        return prettyName

    @property
    def get_absolute_image_url(self):
        return "{}/{}".format(settings.MEDIA_ROOT, 
                               os.path.basename(self.icon.url))
    

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)







# dynamic models follow below

class SteamUser(models.Model):
    ''' Model representing a Steam User '''

    # steam names are not unique, also
    # all unexposed dota users will end up with
    # the valveID = 4294967295
    valveID = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=100,unique=False,blank=True)

    def __str__(self):
        return str(self.name)

class Match(models.Model):
    ''' Model representing a single game '''
    class Meta:
        verbose_name_plural = 'Matches'
    matchID = models.BigIntegerField(unique=True)
    match_seq_num = models.BigIntegerField(unique=True)
    game_mode = models.IntegerField(null=True)
    region = models.IntegerField(null=True)
    patch = models.IntegerField(null=True)
    start_time = models.BigIntegerField()
    duration = models.IntegerField()
    human_players = models.IntegerField()
    radiant_win = models.BooleanField()
    bans = models.ManyToManyField(Hero)

    def __str__(self):
        return str(self.matchID)


class Player(models.Model):
    ''' Model representing a Player in a single game '''
    class Meta:
        verbose_name_plural = 'Players'
        unique_together = ('valveID','name','hero','matchID')

    team_choices = ( ('RADIANT','Radiant'),
                     ('DIRE','Dire'),
        )
        
    valveID = models.ForeignKey(SteamUser,on_delete=models.CASCADE)
    hero = models.ForeignKey(Hero,on_delete=models.CASCADE)
    matchID = models.ForeignKey(Match,on_delete=models.CASCADE)

    # name is distinct from SteamUser.name due to anonymous Players
    name = models.CharField(max_length=100,blank=True) 
    team = models.CharField(max_length=10,choices=team_choices)
    wonMatch = models.BooleanField(default=False)

    slug = models.SlugField(null=True,blank=True)

    def __str__(self):
        labelStr = '{} {} {}'.format(self.hero,self.matchID,self.name)
        return str(labelStr)

    def save(self, *args, **kwargs):
        labelStr = '{} {} {}'.format(self.hero,self.matchID,self.name)
        self.slug = slugify(labelStr)
        super().save(*args, **kwargs)

class ChatEntry(models.Model):

    class Meta:
        verbose_name_plural = 'ChatEntries'

    player = models.ForeignKey(Player,on_delete=models.CASCADE)

    chatTime = models.FloatField()
    chatText = models.TextField(blank=True)

    def __str__(self):
        labelStr = '{}: {}'.format(self.player.hero.name,self.chatText)
        return str(labelStr)


