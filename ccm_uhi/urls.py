from django.conf import settings
from django.shortcuts import HttpResponse
from django.urls import path
from rest_framework.routers import DefaultRouter, SimpleRouter

from ccm_uhi.api.appointment import AppointmentViewSet
from ccm_uhi.api.enquiry import ServiceAvailabilityView


def healthy(request):
    return HttpResponse("OK")


router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register(r"appointment", AppointmentViewSet, basename="care_uhi")

urlpatterns = [
    path("health", healthy),
    path("service_availability/", ServiceAvailabilityView.as_view(), name="service_availability"),
] + router.urls


