from django.urls import path

from genealogy.views import (
    GenealogyRootsView,
    GenealogySearchView,
    GenealogyTreeView,
    ShiftAssociateView,
    UplineView,
)

urlpatterns = [
    path("tree/", GenealogyTreeView.as_view(), name="genealogy-tree"),
    path("roots/", GenealogyRootsView.as_view(), name="genealogy-roots"),
    path("search/", GenealogySearchView.as_view(), name="genealogy-search"),
    path("upline/<str:associate_id>/", UplineView.as_view(), name="genealogy-upline"),
    path("shift/", ShiftAssociateView.as_view(), name="genealogy-shift"),
]
