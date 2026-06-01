"""
Celery tasks for patient notification processing.

Sends booking lifecycle notifications (booking, reschedule, cancellation),
appointment reminders, and queue management alerts.
"""

import logging
from datetime import datetime, timedelta

from celery import shared_task
from django.utils import timezone

from ccm_uhi.services.notification_service import (
    get_patient_abha_identifier,
    send_patient_notification,
)

from care.emr.models.scheduling.booking import TokenBooking
from care.emr.models.scheduling.token import Token
from care.emr.resources.scheduling.slot.spec import BookingStatusChoices

logger = logging.getLogger(__name__)

QUEUE_NOTIFICATION_META_KEY = "ccm_uhi_queue_notifications"
TOKEN_TERMINAL_STATUSES = {"cancelled", "completed", "fulfilled", "closed"}
TOKEN_CALLED_STATUSES = {"called", "in_progress", "ongoing", "serving"}


def _format_slot_dt(slot) -> str:
    if not slot or not slot.start_datetime:
        return ""
    dt = slot.start_datetime
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M")
    return str(dt)


def _get_practitioner_name(slot) -> str:
    if slot and slot.resource and getattr(slot.resource, "user", None):
        user = slot.resource.user
        return getattr(user, "get_full_name", lambda: "")() or getattr(user, "username", "")
    return ""


def _get_token_label(booking: TokenBooking) -> str:
    if not booking.token:
        return ""
    shorthand = getattr(booking.token.category, "shorthand", "") or "T"
    return f"{shorthand}-{booking.token.number}"


def _send_booking_notification(booking: TokenBooking, fortype: str, message: str) -> None:
    patientid = get_patient_abha_identifier(booking.patient)
    if not patientid:
        logger.info(
            "Skipping notification for booking=%s because patient ABHA identifier is missing",
            booking.external_id,
        )
        return
    logger.info(
        "Dispatching booking notification from celery task fortype=%s booking=%s",
        fortype,
        booking.external_id,
    )
    response = send_patient_notification(
        fortype=fortype,
        patientid=patientid,
        notificationmessage=message,
    )
    logger.info(
        "Completed booking notification fortype=%s booking=%s status=%s message=%s",
        fortype,
        booking.external_id,
        response.get("status"),
        response.get("message"),
    )


@shared_task(bind=True, max_retries=2, default_retry_delay=5, acks_late=True)
def send_booking_lifecycle_notification(self, booking_id: int, event_type: str):
    """Send async notification for booking/reschedule/cancellation events."""
    logger.info(
        "Celery booking lifecycle notification started booking_id=%s event_type=%s",
        booking_id,
        event_type,
    )
    try:
        booking = TokenBooking.objects.select_related(
            "patient",
            "token",
            "token_slot",
            "token_slot__resource",
            "token_slot__resource__user",
        ).get(id=booking_id)
    except TokenBooking.DoesNotExist:
        logger.warning("Booking %s not found for notification event %s", booking_id, event_type)
        return

    slot = booking.token_slot
    practitioner_name = _get_practitioner_name(slot)
    token_label = _get_token_label(booking)

    appointment_dt = _format_slot_dt(slot)

    if event_type == "booking":
        message = (
            "Your appointment has been booked successfully. "
            f"Booking ID: {booking.external_id}, "
            f"Patient: {booking.patient.name}, "
            f"Practitioner: {practitioner_name or 'Assigned Practitioner'}, "
            f"Date & Time: {appointment_dt}"
        )
        if token_label:
            message += f", Token Number: {token_label}"
        _send_booking_notification(booking, "Booking", message)
        return

    if event_type == "reschedule":
        message = (
            "Your appointment has been rescheduled. "
            f"Booking ID: {booking.external_id}, "
            f"Patient: {booking.patient.name}, "
            f"Practitioner: {practitioner_name or 'Assigned Practitioner'}, "
            f"New Date & Time: {appointment_dt}"
        )
        if token_label:
            message += f", Token Number: {token_label}"
        _send_booking_notification(booking, "Reschedule", message)
        return

    if event_type == "cancellation":
        message = (
            "Your appointment has been cancelled. "
            f"Booking ID: {booking.external_id}, "
            f"Patient: {booking.patient.name}"
        )
        _send_booking_notification(booking, "Cancellation", message)
        return

    logger.info("Unsupported booking event_type=%s for booking=%s", event_type, booking.external_id)


@shared_task(bind=True, max_retries=2, default_retry_delay=5, acks_late=True)
def send_booking_reminder(self, booking_id: int):
    """Send a reminder to the patient one hour before the appointment."""
    logger.info("Celery booking reminder task started booking_id=%s", booking_id)
    try:
        booking = TokenBooking.objects.select_related(
            "patient",
            "token",
            "token_slot",
            "token_slot__resource",
            "token_slot__resource__user",
        ).get(id=booking_id)
    except TokenBooking.DoesNotExist:
        logger.warning("Booking %s not found for reminder notification", booking_id)
        return

    if booking.status != BookingStatusChoices.booked.value or not booking.token_id:
        logger.info(
            "Skipping reminder for booking=%s because status=%s token_id=%s",
            booking.external_id,
            booking.status,
            booking.token_id,
        )
        return

    slot = booking.token_slot
    if not slot or not slot.start_datetime:
        logger.info("Skipping reminder for booking=%s because slot start time is missing", booking.external_id)
        return

    reminder_at = slot.start_datetime - timedelta(hours=1)
    if timezone.is_naive(reminder_at):
        reminder_at = timezone.make_aware(reminder_at, timezone.get_current_timezone())

    if reminder_at > timezone.now():
        send_booking_reminder.apply_async(args=[booking.id], eta=reminder_at)
        return

    practitioner_name = _get_practitioner_name(slot)
    token_label = _get_token_label(booking)
    appointment_dt = _format_slot_dt(slot)

    message = (
        "Reminder: Your appointment is scheduled in 1 hour. "
        f"Booking ID: {booking.external_id}, "
        f"Patient: {booking.patient.name}, "
        f"Practitioner: {practitioner_name or 'Assigned Practitioner'}, "
        f"Date & Time: {appointment_dt}"
    )
    if token_label:
        message += f", Token Number: {token_label}"

    _send_booking_notification(booking, "Reminder", message)


def _is_active_token(token: Token) -> bool:
    status = (token.status or "").strip().lower()
    return status not in TOKEN_TERMINAL_STATUSES


def _queue_notification_flags(token: Token) -> set[str]:
    meta = token.meta or {}
    flags = meta.get(QUEUE_NOTIFICATION_META_KEY, [])
    return {str(x) for x in flags}


def _set_queue_notification_flag(token: Token, flag: str) -> None:
    meta = token.meta or {}
    flags = _queue_notification_flags(token)
    if flag in flags:
        return
    flags.add(flag)
    meta[QUEUE_NOTIFICATION_META_KEY] = sorted(flags)
    token.meta = meta
    token.save(update_fields=["meta", "modified_date"])


@shared_task(bind=True, max_retries=1, default_retry_delay=5, acks_late=True)
def evaluate_queue_notifications(self, token_id: int):
    """Evaluate queue milestones and send notifications to impacted patients."""
    try:
        token = Token.objects.select_related("queue", "category").get(id=token_id)
    except Token.DoesNotExist:
        logger.warning("Token %s not found for queue notification evaluation", token_id)
        return

    queryset = (
        Token.objects.filter(queue=token.queue, category=token.category)
        .select_related("patient", "booking", "category")
        .order_by("number", "id")
    )
    active_tokens = [t for t in queryset if _is_active_token(t)]
    has_current_called = any(
        (t.status or "").strip().lower() in TOKEN_CALLED_STATUSES for t in active_tokens
    )
    next_position = 2 if has_current_called else 1

    for position, queue_token in enumerate(active_tokens, start=1):
        flags = _queue_notification_flags(queue_token)
        patientid = get_patient_abha_identifier(queue_token.patient)
        if not patientid:
            continue

        base = (
            f"Queue update for token {getattr(queue_token.category, 'shorthand', 'T')}-{queue_token.number}. "
            f"Current queue position: {position}."
        )

        if position == 5 and "position_5" not in flags:
            send_patient_notification(
                fortype="QueueManagement",
                patientid=patientid,
                notificationmessage=f"{base} You are 5th in the queue.",
            )
            _set_queue_notification_flag(queue_token, "position_5")
            continue

        if position == next_position and "next_in_queue" not in flags:
            send_patient_notification(
                fortype="QueueManagement",
                patientid=patientid,
                notificationmessage=f"{base} You are next in the queue.",
            )
            _set_queue_notification_flag(queue_token, "next_in_queue")

        status = (queue_token.status or "").strip().lower()
        if status in TOKEN_CALLED_STATUSES and "current_called" not in flags:
            send_patient_notification(
                fortype="QueueManagement",
                patientid=patientid,
                notificationmessage=f"{base} Your token is currently being called.",
            )
            _set_queue_notification_flag(queue_token, "current_called")


@shared_task(bind=True, max_retries=1, default_retry_delay=5, acks_late=True)
def notify_booking_cancelled_from_status(self, booking_id: int):
    """Compatibility task to notify cancellation if booking status transitions externally."""
    try:
        booking = TokenBooking.objects.only("id", "status").get(id=booking_id)
    except TokenBooking.DoesNotExist:
        return
    if booking.status == BookingStatusChoices.cancelled.value:
        send_booking_lifecycle_notification.delay(booking_id, "cancellation")
