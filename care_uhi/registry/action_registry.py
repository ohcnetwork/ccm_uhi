"""
Action Registry: Lazily resolves Beckn action → service class.
"""

import importlib
import logging

logger = logging.getLogger(__name__)

SERVICE_MODULE_PATH = "care_uhi.services"


def _resolve_service(action: str):
    """
    Dynamically resolve a service class for the given Beckn action.

    """
    module_name = f"{SERVICE_MODULE_PATH}.on_{action}_service"
    class_name = f"On{action.capitalize()}Service"
    try:
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    except (ModuleNotFoundError, AttributeError):
        logger.error("No service found for action: %s", action)
        return None


def get_service(action: str):
    """Resolve a Beckn action to its service instance."""
    service_cls = _resolve_service(action)
    if not service_cls:
        msg = f"Unsupported Beckn action: {action}"
        raise ValueError(msg)
    return service_cls()


def get_callback_action(action: str) -> str:
    """Derive the on_* callback action for any inbound action."""
    return f"on_{action}"
