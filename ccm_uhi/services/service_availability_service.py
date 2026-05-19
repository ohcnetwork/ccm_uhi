import logging
from django.db.models import Q
from care.facility.models.facility import Facility
from care.emr.models.healthcare_service import HealthcareService
from ccm_uhi.mappers.catalog_mapper import map_facility_to_provider

logger = logging.getLogger(__name__)


class ServiceAvailabilityService:
    """Return healthcare services available at facilities with optional filters."""

    def execute(
        self,
        facility_external_id: str | None = None,
        facility_pincode: int | None = None,
        service_names: str | list[str] | None = None,
    ) -> dict:
        filters={
                "facility__isnull": False,
                "facility__is_active": True,
                "deleted": False,
        }
        if service_names:
            if not isinstance(service_names, list):
                service_names = [service_names]
            name_q = Q()
            for name in service_names:
                name_q |= Q(name__icontains=name)
            filters_q = Q(**filters) & name_q
        else:
            filters_q = Q(**filters)

        if facility_external_id:
            filters_q &= Q(facility__external_id=facility_external_id)

        if facility_pincode:
            filters_q &= Q(facility__pincode=facility_pincode)

        hs_qs = HealthcareService.objects.filter(filters_q).select_related("facility", "managing_organization")

        facility_services: dict[int, tuple[Facility, list[dict]]] = {}
        for hs in hs_qs:
            facility = hs.facility
            if facility.id not in facility_services:
                facility_services[facility.id] = (facility, [])

            mang_dept = {}
            if hs.managing_organization:
                mang_dept = {
                    "id": str(hs.managing_organization.external_id),
                    "name": hs.managing_organization.name,
                }

            facility_services[facility.id][1].append({
                "id": str(hs.external_id),
                "name": hs.name,
                "managing_department": mang_dept,
            })

        # Only include facilities that have ALL requested services
        providers = []
        for facility, services in facility_services.values():
            if service_names and len(service_names) > 1:
                matched_names = {s["name"].lower() for s in services}
                if not all(
                    any(sn.lower() in m for m in matched_names)
                    for sn in service_names
                ):
                    continue
            provider = map_facility_to_provider(facility)
            provider["services"] = services
            providers.append(provider)

        return {"providers": providers}
