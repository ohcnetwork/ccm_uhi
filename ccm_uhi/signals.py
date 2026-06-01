import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from care.emr.models.scheduling.booking import TokenBooking
from care.emr.models.scheduling.token import Token
from care.emr.resources.scheduling.slot.spec import BookingStatusChoices

from ccm_uhi.tasks.beckn_tasks import (
	evaluate_queue_notifications,
	send_booking_lifecycle_notification,
)

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=TokenBooking)
def cache_previous_booking_state(sender, instance: TokenBooking, **kwargs):
	if not instance.pk:
		instance._ccm_prev_status = None
		instance._ccm_prev_token_id = None
		return

	previous = TokenBooking.objects.filter(pk=instance.pk).only("status", "token_id").first()
	instance._ccm_prev_status = previous.status if previous else None
	instance._ccm_prev_token_id = previous.token_id if previous else None


@receiver(post_save, sender=TokenBooking)
def booking_lifecycle_notification_handler(sender, instance: TokenBooking, created: bool, **kwargs):
	prev_status = getattr(instance, "_ccm_prev_status", None)
	prev_token_id = getattr(instance, "_ccm_prev_token_id", None)

	if (
		instance.status == BookingStatusChoices.booked.value
		and instance.token_id
		and (prev_status != BookingStatusChoices.booked.value or prev_token_id != instance.token_id)
	):
		send_booking_lifecycle_notification.delay(instance.id, "booking")
		return

	if prev_status != BookingStatusChoices.rescheduled.value and instance.status == BookingStatusChoices.rescheduled.value:
		send_booking_lifecycle_notification.delay(instance.id, "reschedule")
		return

	if prev_status != BookingStatusChoices.cancelled.value and instance.status == BookingStatusChoices.cancelled.value:
		send_booking_lifecycle_notification.delay(instance.id, "cancellation")


@receiver(pre_save, sender=Token)
def cache_previous_token_state(sender, instance: Token, **kwargs):
	if not instance.pk:
		instance._ccm_prev_status = None
		instance._ccm_prev_number = None
		instance._ccm_prev_queue_id = None
		instance._ccm_prev_category_id = None
		return

	previous = (
		Token.objects.filter(pk=instance.pk)
		.only("status", "number", "queue_id", "category_id")
		.first()
	)
	instance._ccm_prev_status = previous.status if previous else None
	instance._ccm_prev_number = previous.number if previous else None
	instance._ccm_prev_queue_id = previous.queue_id if previous else None
	instance._ccm_prev_category_id = previous.category_id if previous else None


@receiver(post_save, sender=Token)
def token_queue_notification_handler(sender, instance: Token, created: bool, **kwargs):
	prev_status = getattr(instance, "_ccm_prev_status", None)
	prev_number = getattr(instance, "_ccm_prev_number", None)
	prev_queue_id = getattr(instance, "_ccm_prev_queue_id", None)
	prev_category_id = getattr(instance, "_ccm_prev_category_id", None)

	should_evaluate = created or any(
		[
			prev_status != instance.status,
			prev_number != instance.number,
			prev_queue_id != instance.queue_id,
			prev_category_id != instance.category_id,
		]
	)
	if not should_evaluate:
		return

	evaluate_queue_notifications.delay(instance.id)
