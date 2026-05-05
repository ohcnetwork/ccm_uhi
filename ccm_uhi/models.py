"""
UHI Beckn Protocol models.

Currently commented out — the plugin operates in synchronous mode
without persisting Beckn protocol state to the database.
"""

# import uuid
#
# from django.db import models
#
#
# class BecknTransaction(models.Model):
#     """Tracks a Beckn transaction across the full request lifecycle."""
#
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     transaction_id = models.UUIDField(db_index=True)
#     message_id = models.UUIDField(unique=True, db_index=True)
#     consumer_id = models.CharField(max_length=512)
#     consumer_uri = models.URLField(max_length=1024)
#     domain = models.CharField(max_length=255, default="nic2004:85111")
#     action = models.CharField(max_length=50)
#     version = models.CharField(max_length=20, default="1.1.0")
#     payload = models.JSONField(default=dict)
#     response_payload = models.JSONField(default=dict, blank=True)
#     status = models.CharField(max_length=20)
#     error = models.JSONField(default=dict, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         db_table = "ccm_uhi_beckntransaction"
#         ordering = ["-created_at"]
#         constraints = [
#             models.UniqueConstraint(
#                 fields=["transaction_id", "action"],
#                 name="unique_transaction_action",
#             )
#         ]
#
#     def __str__(self):
#         return f"{self.action}:{self.transaction_id}"
#
#
# class BecknOrder(models.Model):
#     """
#     Links a Beckn order to a CARE TokenBooking.
#
#     This is the sole bridge between Beckn protocol state and CARE domain.
#     All CARE data is accessed via the `booking` FK — nothing is copied.
#     """
#
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     order_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
#     transaction_id = models.UUIDField(db_index=True)
#     booking = models.OneToOneField(
#         "emr.TokenBooking",
#         on_delete=models.CASCADE,
#         related_name="beckn_order",
#         null=True,
#         blank=True,
#     )
#     status = models.CharField(max_length=30)
#     consumer_id = models.CharField(max_length=512)
#     consumer_uri = models.URLField(max_length=1024)
#     provider_id = models.CharField(max_length=255, blank=True, default="")
#     item_id = models.CharField(max_length=255, blank=True, default="")
#     fulfillment_id = models.CharField(max_length=255, blank=True, default="")
#     billing = models.JSONField(default=dict, blank=True)
#     quote = models.JSONField(default=dict, blank=True)
#     payment = models.JSONField(default=dict, blank=True)
#     terms = models.JSONField(default=list, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         db_table = "ccm_uhi_becknorder"
#         ordering = ["-created_at"]
#
#     def __str__(self):
#         return f"Order:{self.beckn_order_id} ({self.status})"

