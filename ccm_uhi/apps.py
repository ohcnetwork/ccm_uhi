from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

PLUGIN_NAME = "ccm_uhi"


class CcmUhiConfig(AppConfig):
    name = PLUGIN_NAME
    verbose_name = _("Care CCM UHI")

    def ready(self):
        import ccm_uhi.signals  # noqa F401
