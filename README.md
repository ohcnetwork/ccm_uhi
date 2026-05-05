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
