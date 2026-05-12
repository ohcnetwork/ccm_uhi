
import logging

from django.utils import timezone

from care.emr.models.organization import FacilityOrganization, FacilityOrganizationUser
from care.emr.models.scheduling.schedule import (
    Schedule,
    SchedulableResource,
)
from care.facility.models.facility import Facility
from ccm_uhi.mappers.catalog_mapper import (
    map_facility_to_provider,
    map_user_to_agent,
    resolve_facility,
)
from ccm_uhi.constants import CARE_CATALOG_DESCRIPTOR

logger = logging.getLogger(__name__)


class OnSearchService:
    """Return providers with facility locations and departments that have schedulable resources."""

    def execute(self, context: dict, message: dict) -> dict:
        provider_id = message.get("provider_id")

        if provider_id:
            try:
                facilities = [resolve_facility(provider_id)]
            except ValueError:
                logger.warning("Provided provider_id not found: %s", provider_id)
                return {"providers": []}
        else:
            facilities = self._find_facilities_with_resources()

        if not facilities:
            return {"providers": []}

        providers = []
        for facility in facilities:
            resources = self._find_active_resources(facility)
            if not resources:
                continue

            departments = self._build_department_catalog(facility, resources)
            if not departments:
                continue

            provider = map_facility_to_provider(facility)
            provider["departments"] = departments
            providers.append(provider)

        return {
            "descriptor": CARE_CATALOG_DESCRIPTOR,
            "providers": providers,
        }

    def _find_facilities_with_resources(self) -> list[Facility]:
        """Find all active facilities that have at least one active schedulable resource."""
        now = timezone.now()
        facility_ids = (
            SchedulableResource.objects.filter(
                deleted=False,
                resource_type="practitioner",
                user__isnull=False,
                schedule__valid_to__gte=now,
                schedule__deleted=False,
            )
            .values_list("facility_id", flat=True)
            .distinct()
        )
        return list(Facility.objects.filter(id__in=facility_ids, is_active=True))

    def _find_active_resources(self, facility) -> list[SchedulableResource]:
        """Find practitioner resources that have at least one valid schedule."""
        now = timezone.now()
        return list(
            SchedulableResource.objects.filter(
                deleted=False,
                facility=facility,
                resource_type="practitioner",
                user__isnull=False,
                schedule__valid_to__gte=now,
                schedule__deleted=False,
            )
            .select_related("user")
            .distinct()
        )

    def _build_department_catalog(
        self, facility, resources: list[SchedulableResource]
    ) -> list[dict]:
        """Build departments that have schedulable resources, each with its resource list."""
        user_ids = [r.user_id for r in resources]

        # Map user_id → resource for quick lookup
        user_resource_map: dict[int, SchedulableResource] = {}
        for r in resources:
            user_resource_map[r.user_id] = r

        dept_users = (
            FacilityOrganizationUser.objects.filter(
                organization__facility=facility,
                organization__org_type="dept",
                organization__active=True,
                user_id__in=user_ids,
            )
            .select_related("organization", "user", "role")
        )

        # Build dept_id → {org, resources} mapping
        # First pass: build complete user_id → departments map
        user_dept_map: dict[int, list[dict]] = {}
        for du in dept_users:
            user_dept_map.setdefault(du.user_id, []).append({
                "id": str(du.organization.external_id),
                "name": du.organization.name,
            })

        # Second pass: group practitioners into departments (with full dept lists)
        dept_map: dict[int, dict] = {}
        seen_dept_user: set[tuple[int, int]] = set()
        assigned_user_ids: set[int] = set()
        for du in dept_users:
            dept_id = du.organization_id
            if dept_id not in dept_map:
                dept_map[dept_id] = {
                    "org": du.organization,
                    "practitioners": [],
                }
            # Avoid duplicate user in same department
            if (dept_id, du.user_id) in seen_dept_user:
                continue
            seen_dept_user.add((dept_id, du.user_id))

            resource = user_resource_map.get(du.user_id)
            if resource and resource.user:
                role_name = du.role.name if du.role else ""
                agent = map_user_to_agent(resource.user, role=role_name, departments=user_dept_map.get(du.user_id, []))
                dept_map[dept_id]["practitioners"].append(agent)
                assigned_user_ids.add(du.user_id)

        # Only include departments that have schedulable resources
        departments = []
        for dept_info in dept_map.values():
            org = dept_info["org"]
            if dept_info["practitioners"]:
                departments.append(
                    {
                        "id": str(org.external_id),
                        "name": org.name,
                        "description": org.description or "",
                        "practitioners": dept_info["practitioners"],
                    }
                )

        # Include resources not assigned to any department under "General"
        unassigned = [
            user_resource_map[uid]
            for uid in user_ids
            if uid not in assigned_user_ids and user_resource_map.get(uid)
        ]
        if unassigned:
            departments.append(
                {
                    "id": "unassigned",
                    "name": "General",
                    "description": "",
                    "practitioners": [
                        map_user_to_agent(r.user) for r in unassigned if r.user
                    ],
                }
            )

        return departments
