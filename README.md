# Care UHI

Django plugin for ohcnetwork/care.

## Local Development

To develop the plug in local environment along with care, follow the steps below:

1. Go to the care root directory and clone the plugin repository:

```bash
cd care
git clone git@github.com:ohcnetwork/Care UHI.git
```

2. Add the plugin config in plug_config.py

```python
...

Care UHI_plugin = Plug(
    name=Care UHI, # name of the django app in the plugin
    package_name="/app/Care UHI", # this has to be /app/ + plugin folder name
    version="", # keep it empty for local development
    configs={}, # plugin configurations if any
)
plugs = [Care UHI_plugin]

...
```

3. Tweak the code in plugs/manager.py, install the plugin in editable mode

```python
...

subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-e", *packages] # add -e flag to install in editable mode
)

...
```

4. Rebuild the docker image and run the server

```bash
make re-build
make up
```

> [!IMPORTANT]
> Do not push these changes in a PR. These changes are only for local development.

## Production Setup

To install care Care UHI, you can add the plugin config in [care/plug_config.py](https://github.com/ohcnetwork/care/blob/develop/plug_config.py) as follows:

```python
...

Care UHI_plug = Plug(
    name=Care UHI,
    package_name="git+https://github.com/ohcnetwork/Care UHI.git",
    version="@master",
    configs={},
)
plugs = [Care UHI_plug]
...
```

[Extended Docs on Plug Installation](https://care-be-docs.ohc.network/pluggable-apps/configuration.html)

## API Reference

All endpoints are under the `/appointment/` router and accept `POST` requests with no authentication required.

### 1. Search

**`POST /appointment/search/`**

Searches for available healthcare providers/services within a date range.

```json
{
  "context": {
    "domain": "<string: domain code>",
    "country": "<string: ISO 3166-1 alpha-3>",
    "action": "search",
    "transaction_id": "<uuid>",
    "message_id": "<uuid>",
    "consumer_id": "<string>",
    "consumer_uri": "<url>"
  },
  "message": {
    "intent": {
      "provider_id": "<uuid>",
      "fulfillment": {
        "type": "<string: physical | virtual>",
        "start": { "time": { "timestamp": "<ISO 8601 datetime>" } },
        "end": { "time": { "timestamp": "<ISO 8601 datetime>" } }
      }
    }
  }
}
```

### 2. Select

**`POST /appointment/select/`**

Selects a specific service item and fulfillment from a provider.

```json
{
  "context": {
    "domain": "<string: domain code>",
    "country": "<string: ISO 3166-1 alpha-3>",
    "action": "select",
    "transaction_id": "<uuid>",
    "message_id": "<uuid>",
    "consumer_id": "<string>",
    "consumer_uri": "<url>"
  },
  "message": {
    "order": {
      "descriptor_id": "<uuid>",
      "item_id": "<uuid>",
      "fulfillment_id": "<uuid>"
    }
  }
}
```

### 3. Init

**`POST /appointment/init/`**

Initializes an order with patient billing details.

```json
{
  "context": {
    "domain": "<string: domain code>",
    "country": "<string: ISO 3166-1 alpha-3>",
    "action": "init",
    "transaction_id": "<uuid>",
    "message_id": "<uuid>",
    "consumer_id": "<string>",
    "consumer_uri": "<url>"
  },
  "message": {
    "order": {
      "descriptor_id": "<uuid>",
      "item_id": "<uuid>",
      "fulfillment_id": "<uuid>",
      "billing": {
        "name": "<string>",
        "gender": "<string: male | female | transgender>",
        "date_of_birth": "<date: YYYY-MM-DD>",
        "year_of_birth": "<integer>",
        "blood_group": "<string: blood group enum>",
        "phone_number": "<string: E.164 phone>",
        "emergency_phone_number": "<string: E.164 phone>",
        "address": "<string>",
        "permanent_address": "<string>",
        "pincode": "<integer>",
        "geo_organization": "<string: state name>"
      }
    }
  }
}
```

### 4. Confirm

**`POST /appointment/confirm/`**

Confirms an order with agreed terms. Requires a valid `order_id` from a prior init/select flow.

```json
{
  "context": {
    "domain": "<string: domain code>",
    "country": "<string: ISO 3166-1 alpha-3>",
    "action": "confirm",
    "transaction_id": "<uuid>",
    "message_id": "<uuid>",
    "consumer_id": "<string>",
    "consumer_uri": "<url>"
  },
  "message": {
    "order_id": "<uuid>",
    "terms": [
      {
        "type": "<string: settlement | payment | cancellation>",
        "terms_state": "<string: agreed | disagreed>"
      }
    ]
  }
}
```

### 5. Status

**`POST /appointment/status/`**

Checks the status of an existing order. Requires a valid `order_id`.

```json
{
  "context": {
    "domain": "<string: domain code>",
    "country": "<string: ISO 3166-1 alpha-3>",
    "action": "status",
    "transaction_id": "<uuid>",
    "message_id": "<uuid>",
    "consumer_id": "<string>",
    "consumer_uri": "<url>"
  },
  "message": {
    "order_id": "<uuid>"
  }
}
```

### 6. Cancel

**`POST /appointment/cancel/`**

Cancels an existing order. Requires a valid `order_id`.

```json
{
  "context": {
    "domain": "<string: domain code>",
    "country": "<string: ISO 3166-1 alpha-3>",
    "action": "cancel",
    "transaction_id": "<uuid>",
    "message_id": "<uuid>",
    "consumer_id": "<string>",
    "consumer_uri": "<url>"
  },
  "message": {
    "order_id": "<uuid>"
  }
}
```

This plugin was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) using the [ohcnetwork/care-plugin-cookiecutter](https://github.com/ohcnetwork/care-plugin-cookiecutter).

---

## Notifications

Patient notifications are pushed to the CCM gateway endpoint as fire-and-forget HTTP POST requests. They are triggered automatically via Django signals on booking/token state changes and dispatched through Celery tasks.

### Payload Format

All notifications are sent as JSON with this structure:

```json
{
  "requestid": "<UUID>",
  "fortype": "<string: notification type>",
  "patientid": "<string: patient ABHA identifier>",
  "notificationmessage": "<string: human-readable message>"
}
```

### Notification Types & Triggers

#### 1. Booking Confirmation

**Trigger:** `TokenBooking` status changes to `booked` with a token assigned.

**fortype:** `Booking`

```json
{
  "requestid": "EBA5D680-7989-4CF6-9B2A-3AF06030F5CA",
  "fortype": "Booking",
  "patientid": "91674538728603",
  "notificationmessage": "Your appointment has been booked successfully. Booking ID: 30d00ccc-3121-4b15-b12e-45a1ac174f42, Patient: John Doe, Practitioner: Dr. Smith, Date & Time: 2026-06-01 10:00, Token Number: ccm-5"
}
```

#### 2. Reschedule

**Trigger:** Reschedule API calls `OnConfirmService` internally to create a new booking, which triggers a `Booking` notification for the new appointment (same as a fresh booking).

**fortype:** `Booking`

```json
{
  "requestid": "A1B2C3D4-5678-90AB-CDEF-1234567890AB",
  "fortype": "Booking",
  "patientid": "91674538728603",
  "notificationmessage": "Your appointment has been booked successfully. Booking ID: 30d00ccc-3121-4b15-b12e-45a1ac174f42, Patient: John Doe, Practitioner: Dr. Smith, New Date & Time: 2026-06-02 14:00, Token Number: ccm-5"
}
```

> **Note:** A reschedule also cancels the old booking, which triggers a separate `Cancellation` notification for the original appointment.

#### 3. Cancellation

**Trigger:** `TokenBooking` status changes to `cancelled`.

**fortype:** `Cancellation`

```json
{
  "requestid": "F1E2D3C4-B5A6-9780-1234-ABCDEF567890",
  "fortype": "Cancellation",
  "patientid": "91674538728603",
  "notificationmessage": "Your appointment has been cancelled. Booking ID: 30d00ccc-3121-4b15-b12e-45a1ac174f42, Patient: John Doe"
}
```

#### 4. Reminder (1 hour before appointment)

**Trigger:** Scheduled automatically when a booking is confirmed; fires 1 hour before the slot start time.

**fortype:** `Reminder`

```json
{
  "requestid": "12345678-ABCD-EF01-2345-6789ABCDEF01",
  "fortype": "Reminder",
  "patientid": "91674538728603",
  "notificationmessage": "Reminder: Your appointment is scheduled in 1 hour. Booking ID: 30d00ccc-3121-4b15-b12e-45a1ac174f42, Patient: John Doe, Practitioner: Dr. Smith, Date & Time: 2026-06-01 10:00, Token Number: ccm-5"
}
```

#### 5. Queue Management — Position 5

**Trigger:** Patient's token reaches position 5 in the active queue.

**fortype:** `QueueManagement`

```json
{
  "requestid": "AABBCCDD-1122-3344-5566-778899AABBCC",
  "fortype": "QueueManagement",
  "patientid": "91674538728603",
  "notificationmessage": "Queue update for token ccm-11. Current queue position: 5. You are 5th in the queue."
}
```

#### 6. Queue Management — Next in Queue

**Trigger:** Patient's token is next to be called (position immediately after the currently-called token).

**fortype:** `QueueManagement`

```json
{
  "requestid": "11223344-AABB-CCDD-EEFF-556677889900",
  "fortype": "QueueManagement",
  "patientid": "91674538728603",
  "notificationmessage": "Queue update for token ccm-12. Current queue position: 2. You are next in the queue."
}
```

#### 7. Queue Management — Token Called

**Trigger:** Patient's token status changes to `called` / `in_progress` / `ongoing` / `serving`.

**fortype:** `QueueManagement`

```json
{
  "requestid": "EBA5D680-7989-4CF6-9B2A-3AF06030F5CA",
  "fortype": "QueueManagement",
  "patientid": "91674538728603",
  "notificationmessage": "Queue update for token ccm-11. Current queue position: 7. Your token is currently being called."
}
```

### Notification Flow

1. Django signal (`post_save` on `TokenBooking` or `Token`) fires
2. Celery task is dispatched (`.delay()`)
3. Task resolves the patient's ABHA identifier
4. `send_patient_notification()` builds payload and POSTs to endpoint
5. Response is logged; failures are retried (max 2 retries)
