from django.contrib import admin

from .models import Collection, CollectionSound

# Register your models here.


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    fields = ["user", "name", "num_sounds", "public", "featured_sound_ids", "description"]
    filter_horizontal = ["sounds"]
    list_display = ("name", "user", "num_sounds", "public")
    readonly_fields = ["created"]
    actions = ["make_public", "make_private"]
    raw_id_fields = ["user"]

    def get_sounds(self, obj):
        return ", ".join(str(sound.id) for sound in obj.sounds.all())

    get_sounds.short_description = "Sounds"

    def save_related(self, request, form, formsets, change):
        # sounds m2m is saved here (after save_model), so mark them dirty once it's up to date
        super().save_related(request, form, formsets, change)
        form.instance.sounds.update(is_index_dirty=True)

    @admin.action(description="Make selected collections public")
    def make_public(self, request, queryset):
        queryset.update(public=True)

    @admin.action(description="Make selected collection private")
    def make_private(self, request, queryset):
        queryset.update(public=False)


@admin.register(CollectionSound)
class CollectionSoundAdmin(admin.ModelAdmin):
    list_display = ("collection", "sound", "status")
    list_filter = ("status",)
    search_fields = ("collection__name", "sound__id")
    raw_id_fields = ("collection", "sound")
