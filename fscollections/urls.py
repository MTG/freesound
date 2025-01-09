from django.urls import path
from . import views

urlpatterns = [
    path('',views.collections, name='collections'),
    path('<int:collection_id>/', views.collections, name='collections')
]