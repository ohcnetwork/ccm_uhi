import logging

from care.emr.models.healthcare_service import HealthcareService
from care.facility.models.facility import Facility
from ccm_uhi.mappers.catalog_mapper import map_facility_to_provider

logger = logging.getLogger(__name__)


class ServiceAvailabilityService:
    """Return healthcare services available at facilities with optional filters."""

    def execute(
        self,
        facility_external_id: str | None = None,
        facility_pincode: int | None = None,
        service_name: str | None = None,
    ) -> dict:
        facilities = self._resolve_facilities(facility_external_id, facility_pincode)
        if not facilities:
            return {"providers": []}

        providers = []
        for facility in facilities:
            services = self._get_services(facility, service_name)
            if not services:
                continue
            provider = map_facility_to_provider(facility)
            provider["services"] = services
            providers.append(provider)

        return {"providers": providers}

    def _resolve_facilities(
        self,
        facility_external_id: str | None,
        facility_pincode: int | None,
    ) -> list[Facility]:
        """Resolve facilities by external_id or pincode. Returns all if no filter given."""
        if facility_external_id:
            try:
                return [
                    Facility.objects.get(
                        external_id=facility_external_id, is_active=True
                    )
                ]
            except Facility.DoesNotExist:
                logger.warning(
                    "Facility not found: external_id=%s", facility_external_id
                )
                return []

        if facility_pincode:
            return list(
                Facility.objects.filter(pincode=facility_pincode, is_active=True)
            )

        # No filter provided — return all active facilities
        return list(Facility.objects.filter(is_active=True))

    def _get_services(self, facility: Facility, service_name: str | None) -> list[dict]:
        """Get all healthcare services for a facility, optionally filtered by name."""
        hs_qs = HealthcareService.objects.filter(facility=facility, deleted=False)

        if service_name:
            hs_qs = hs_qs.filter(name__icontains=service_name)

        services = []
        for hs in hs_qs:
            mang_dept = {
            "id": str(hs.managing_organization.external_id),
            "name": hs.managing_organization.name,
            } if hs.managing_organization else {}
            services.append({
                "id": str(hs.external_id),
                "name": hs.name,
                "managing_department": mang_dept,
            })

        return services
