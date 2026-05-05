from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

PLUGIN_NAME = "care_uhi"


class CareUhiConfig(AppConfig):
    name = PLUGIN_NAME
    verbose_name = _("Care uhi")

    def ready(self):
        import care_uhi.signals  # noqa F401
