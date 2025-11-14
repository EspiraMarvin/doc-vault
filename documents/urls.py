from django.urls import path, include
from rest_framework.routers import DefaultRouter
# from .views import DocumentViewSet
from .views import (
    DocumentListCreateAPIView
)

router = DefaultRouter()
# router.register('documents', DocumentViewSet, basename='document')

urlpatterns = [
    # path('', include(router.urls)),
    path('documents/', DocumentListCreateAPIView.as_view(),
         name='documents-list-create'),
]