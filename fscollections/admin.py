from django.contrib import admin
from .models import Collection, CollectionSound

# Register your models here.

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):

    fields = ["user","name", "num_sounds", "public","get_sounds"]
    filter_horizontal =  ["sounds"]
    list_display = ("name", "user", "num_sounds", "public","get_sounds")
    readonly_fields = ["created"]
    actions = ["make_public", "make_private"]

    def has_delete_permission(self, request, obj=None):
        if obj and obj.sounds.count() > 0:
            return False  
        return True

    def get_sounds(self, obj):
        return ", ".join(str(sound.id) for sound in obj.sounds.all())
    get_sounds.short_description = "Sounds"

    @admin.action(description="Make selected collections public")
    def make_public(self, request, queryset):
        queryset.update(public=True)
    
    @admin.action(description="Make selected collection private")
    def make_private(self, request, queryset):
        queryset.update(public=False)