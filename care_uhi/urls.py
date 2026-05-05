from django.conf import settings
from django.shortcuts import HttpResponse
from django.urls import path
from rest_framework.routers import DefaultRouter, SimpleRouter

from care_uhi.api.appointment import AppointmentViewSet


def healthy(request):
    return HttpResponse("OK")


router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register(r"appointment", AppointmentViewSet, basename="care_uhi")

urlpatterns = [
    path("health", healthy),
] + router.urls


