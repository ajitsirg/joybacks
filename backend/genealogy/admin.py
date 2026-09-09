from django.contrib import admin
from unfold.admin import ModelAdmin

from genealogy.models import GenealogyClosure, GenealogyNode


@admin.register(GenealogyNode)
class GenealogyNodeAdmin(ModelAdmin):
    list_display = ("associate", "depth", "leg_index", "parent")
    search_fields = ("associate__associate_id",)
    raw_id_fields = ("associate", "parent")


@admin.register(GenealogyClosure)
class GenealogyClosureAdmin(ModelAdmin):
    list_display = ("ancestor", "descendant", "depth")
    search_fields = ("ancestor__associate_id", "descendant__associate_id")
