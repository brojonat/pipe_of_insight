from django.contrib import admin
from dota_chat import models


# Inlines
class Hero_HeroAbility_Inline(admin.TabularInline):
    model = models.Hero.abilities.through   
    extra = 0

### this is what i want ###
#class User_Match_Inline(admin.TabularInline):
#    #model = models.Player
#    pass
#
#class User_Chat_Inline(admin.TabularInline):
#    #model = models.Player.chat.through
#    pass

# any way to make this editable? This works
class ChatInline(admin.TabularInline):
    model = models.ChatEntry
    fields = ('player','chatTime','chatText')
    readonly_fields = ('player','chatTime','chatText')

######

# Admin classes
class HeroAdmin(admin.ModelAdmin):
    inlines = [Hero_HeroAbility_Inline,]
    list_max_show_all = 500
    list_per_page = 200
    exclude = ('abilities',)

class HeroAbilityAdmin(admin.ModelAdmin):
    list_max_show_all = 5000
    list_per_page = 200

class PlayerAdmin(admin.ModelAdmin):
    raw_id_fields = ('valveID','hero','matchID')
    inlines = [ChatInline]

class ChatAdmin(admin.ModelAdmin):
    raw_id_fields = ('player',)




# Register your models here.
admin.site.register(models.HeroRoles)
admin.site.register(models.Hero,HeroAdmin)
admin.site.register(models.HeroAbility,HeroAbilityAdmin)
admin.site.register(models.AbilityBehaviors)
admin.site.register(models.Item)


admin.site.register(models.SteamUser)
admin.site.register(models.Match)


admin.site.register(models.Player,PlayerAdmin)
admin.site.register(models.ChatEntry,ChatAdmin)

