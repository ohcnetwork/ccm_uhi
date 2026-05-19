# CCM UHI API Documentation

## Base URL

All appointment endpoints are prefixed with `/appointment/`.
The service availability endpoint is at `/service_availability/`.

---

## 1. Search Providers

Search for available healthcare providers/facilities with schedulable resources.

### Endpoint

```
GET /appointment/search/
```

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `provider_id` | `string` | No | Facility external ID (UUID). If omitted, returns all facilities with active resources. |

---

## 2. Select (Get Available Slots)

Get available appointment slots for a specific doctor or department at a facility.

### Endpoint

```
POST /appointment/select/
```

### Request

```json
{
  "context": {
    "message_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1",
    "transaction_id": "d682a4b6-b588-4320-9f6b-2541b96e949f"
  },
  "message": {
    "provider_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1",
    "doctor_id": "7a8377ff-ba7e-4cc5-a5f3-2610f338d0ff",
    "fulfillment": {
      "start": {
        "time": {
          "timestamp": "2026-05-11T09:00:00+05:30"
        }
      },
      "end": {
        "time": {
          "timestamp": "2026-05-11T23:59:00+05:30"
        }
      }
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `context.message_id` | `string` | Yes | Unique message ID (UUID) |
| `context.transaction_id` | `string` | Yes | Transaction ID (UUID) |
| `message.provider_id` | `string` | Yes | Facility external ID |
| `message.doctor_id` | `string` | No | Doctor external ID (at least one of doctor_id or department_id required) |
| `message.department_id` | `string` | No | Department external ID |
| `message.fulfillment.start.time.timestamp` | `string` | No | Start of time window (ISO 8601) |
| `message.fulfillment.end.time.timestamp` | `string` | No | End of time window (ISO 8601) |

### Response

```json
{
  "context": {
    "domain": "nic2004:85110",
    "country": "IND",
    "city": "234e81e4-a4c4-474c-a60e-a8eb5da162ba",
    "action": "select",
    "core_version": "0.0.1",
    "message_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1",
    "transaction_id": "d682a4b6-b588-4320-9f6b-2541b96e949f"
  },
  "message": {
    "descriptor": {
      "name": "CARE - Open Health Care Network",
      "short_desc": "Open-source health care platform by Open Health Care Network (OHC)",
      "images": [
        {
          "url": "https://cdn.ohc.network/care_logo.svg"
        }
      ]
    },
    "providers": [
      {
        "id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1",
        "descriptor": {
          "name": "Choudhry-Bhakta",
          "short_desc": "Odio eum quibusdam. Repellat impedit fugiat esse tenetur autem sint corporis.\nPariatur eum rem. Sequi repellendus natus animi."
        },
        "location": {
          "id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1",
          "gps": "17.9823069999999987,-166.7245249999999999",
          "address": "08/795\nSachar, Bijapur-169669"
        },
        "items": [
          {
            "id": "5976fd2c-024f-4b20-b436-39584355a139",
            "descriptor": {
              "name": "regula op",
              "code": "CONSULTATION"
            },
            "price": {
              "currency": "INR",
              "value": "0"
            },
            "fulfillment_id": "bad8c0c5-e2ae-459d-812e-285d6d21de92",
            "slot_type": "appointment",
            "slot_duration_minutes": 24
          }
        ],
        "fulfillments": [
          {
            "id": "bad8c0c5-e2ae-459d-812e-285d6d21de92",
            "type": "physical",
            "agent": {
              "id": "7a8377ff-ba7e-4cc5-a5f3-2610f338d0ff",
              "name": "Nandini Palla",
              "role": "Doctor"
            },
            "start": {
              "time": {
                "timestamp": "2026-05-11T03:54:00+00:00"
              }
            },
            "end": {
              "time": {
                "timestamp": "2026-05-11T04:18:00+00:00"
              }
            }
          }
        ]
      }
    ]
  }
}
```

---

## 3. Confirm (Book Appointment)

Book an appointment by confirming a specific slot.

### Endpoint

```
POST /appointment/confirm/
```

### Request

```json
{
  "context": {
    "message_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1",
    "transaction_id": "d682a4b6-b588-4320-9f6b-2541b96e949f"
  },
  "message": {
    "provider_id": "688a430b-9c3a-4f79-a7bf-c9c7dadc03c1",
    "fulfillment_id": "e6b9b7c2-629f-4bc4-b035-ce79b1f63112f",
    "patient": {
      "name": "Nihal",
      "abha_number": "66-4695-9532-1984",
      "gender": "male",
      "date_of_birth": "1999-08-25",
      "year_of_birth": 1999,
      "blood_group": "A_positive",
      "phone_number": "+919823423342",
      "address": "Kerala",
      "permanent_address": "Kerala",
      "pincode": 682030
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `context.message_id` | `string` | Yes | Unique message ID (UUID) |
| `context.transaction_id` | `string` | Yes | Transaction ID (UUID) |
| `message.provider_id` | `string` | Yes | Facility external ID |
| `message.fulfillment_id` | `string` | Yes | Slot external ID to book |
| `message.patient.name` | `string` | Yes | Patient name |
| `message.patient.phone_number` | `string` | Yes | Patient phone number |
| `message.patient.abha_number` | `string` | No | ABHA number |
| `message.patient.gender` | `string` | No | Gender (male/female/other) |
| `message.patient.date_of_birth` | `string` | No | Date of birth (YYYY-MM-DD) |
| `message.patient.year_of_birth` | `integer` | No | Year of birth |
| `message.patient.blood_group` | `string` | No | Blood group |
| `message.patient.address` | `string` | No | Current address |
| `message.patient.permanent_address` | `string` | No | Permanent address |
| `message.patient.pincode` | `integer` | No | Pincode |

### Response

```json
{
  "context": {
    "domain": "nic2004:85110",
    "country": "IND",
    "city": "234e81e4-a4c4-474c-a60e-a8eb5da162ba",
    "action": "confirm",
    "core_version": "0.0.1",
    "message_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1",
    "transaction_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1"
  },
  "message": {
    "order_id": "daa7f204-c41b-44bb-b0ac-d010978134f3",
    "status": "booked",
    "provider": {
      "id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1",
      "descriptor": {
        "name": "Choudhry-Bhakta",
        "short_desc": "Odio eum quibusdam. Repellat impedit fugiat esse tenetur autem sint corporis.\nPariatur eum rem. Sequi repellendus natus animi."
      },
      "location": {
        "id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1",
        "gps": "17.9823069999999987,-166.7245249999999999",
        "address": "08/795\nSachar, Bijapur-169669"
      }
    },
    "patient": {
      "id": "f091f30e-20cf-45bd-90b6-4fa3c8943f40",
      "name": "Nihal",
      "gender": "male",
      "phone_number": "+919823423342",
      "date_of_birth": "1999-08-25",
      "address": "Kerala"
    },
    "fulfillment": {
      "id": "d6b9b7c2-629f-4bc4-b035-ce79b1f631aa",
      "type": "physical",
      "agent": {
        "id": "7a8377ff-ba7e-4cc5-a5f3-2610f338d0ff",
        "name": "Nandini Palla",
        "role": ""
      },
      "start": {
        "time": {
          "timestamp": "2026-05-11T03:30:00+00:00"
        }
      },
      "end": {
        "time": {
          "timestamp": "2026-05-11T03:54:00+00:00"
        }
      }
    },
    "token": "GC - 5",
    "item": {
      "id": "5976fd2c-024f-4b20-b436-39584355a139",
      "descriptor": {
        "name": "regula op",
        "code": "CONSULTATION"
      },
      "price": {
        "currency": "INR",
        "value": "0"
      },
      "fulfillment_id": "d6b9b7c2-629f-4bc4-b035-ce79b1f631aa",
      "slot_type": "appointment",
      "slot_duration_minutes": 24
    },
    "quote": {
      "price": {
        "currency": "INR",
        "value": "0"
      },
      "breakup": []
    }
  }
}
```

---

## 4. Status (Check Booking Status)

Check the status of an existing booking.

### Endpoint

```
POST /appointment/status/
```

### Request

```json
{
  "context": {
    "message_id": "81a44c90-9c8d-4b67-be3c-118dd0164061",
    "transaction_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1"
  },
  "message": {
    "order_id": "e7c868bf-7a45-4f97-8047-f28ef6fda65c"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `context.message_id` | `string` | Yes | Unique message ID (UUID) |
| `context.transaction_id` | `string` | Yes | Transaction ID (UUID) |
| `message.order_id` | `string` | Yes | Booking order ID |

### Response

```json
{
  "context": {
    "domain": "nic2004:85110",
    "country": "IND",
    "city": "b6f29715-2786-4cb6-82c2-94ea997bba14",
    "action": "status",
    "core_version": "0.0.1",
    "message_id": "81a44c90-9c8d-4b67-be3c-118dd0164061",
    "transaction_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1"
  },
  "message": {
    "order_id": "e7c868bf-7a45-4f97-8047-f28ef6fda65c",
    "status": "cancelled",
    "patient": {
      "id": "60d4be1f-d0e5-4efb-bc07-30cb40bd00da",
      "name": "Nihal",
      "gender": "male",
      "phone_number": "+919823423342",
      "date_of_birth": "1999-08-25",
      "address": "Kerala"
    },
    "provider": {
      "id": "d682a4b6-b588-4320-9f6b-2541b96e949f",
      "descriptor": {
        "name": "Keonjhar Hospital",
        "short_desc": ""
      },
      "location": {
        "id": "d682a4b6-b588-4320-9f6b-2541b96e949f",
        "gps": "",
        "address": "asd"
      }
    },
    "fulfillment": {
      "id": "199fffd0-83da-4caf-b5f2-0cc73af066b4",
      "type": "physical",
      "agent": {
        "id": "44bcb10f-9bde-43f6-9288-b310827bb914",
        "name": "Dr. Aravind Mahadevan",
        "role": "",
        "departments": []
      },
      "start": {
        "time": {
          "timestamp": "2026-05-13T17:08:00+00:00"
        }
      },
      "end": {
        "time": {
          "timestamp": "2026-05-13T17:19:00+00:00"
        }
      }
    }
  }
}
```

---

## 5. Cancel (Cancel Booking)

Cancel an existing appointment booking.

### Endpoint

```
POST /appointment/cancel/
```

### Request

```json
{
  "context": {
    "message_id": "81a44c90-9c8d-4b67-be3c-118dd0164061",
    "transaction_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1"
  },
  "message": {
    "order_id": "e7c868bf-7a45-4f97-8047-f28ef6fda65c"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `context.message_id` | `string` | Yes | Unique message ID (UUID) |
| `context.transaction_id` | `string` | Yes | Transaction ID (UUID) |
| `message.order_id` | `string` | Yes | Booking order ID to cancel |

### Response

```json
{
  "context": {
    "domain": "nic2004:85110",
    "country": "IND",
    "city": "b6f29715-2786-4cb6-82c2-94ea997bba14",
    "action": "cancel",
    "core_version": "0.0.1",
    "message_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1",
    "transaction_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1"
  },
  "message": {
    "order_id": "e7c868bf-7a45-4f97-8047-f28ef6fda65c",
    "status": "cancelled",
    "patient": {
      "id": "60d4be1f-d0e5-4efb-bc07-30cb40bd00da",
      "name": "Nihal",
      "gender": "male",
      "phone_number": "+919823423342",
      "date_of_birth": "1999-08-25",
      "address": "Kerala"
    },
    "provider": {
      "id": "d682a4b6-b588-4320-9f6b-2541b96e949f",
      "descriptor": {
        "name": "Keonjhar Hospital",
        "short_desc": ""
      },
      "location": {
        "id": "d682a4b6-b588-4320-9f6b-2541b96e949f",
        "gps": "",
        "address": "asd"
      }
    },
    "fulfillment": {
      "id": "199fffd0-83da-4caf-b5f2-0cc73af066b4",
      "type": "physical",
      "agent": {
        "id": "44bcb10f-9bde-43f6-9288-b310827bb914",
        "name": "Dr. Aravind Mahadevan",
        "role": "",
        "departments": []
      },
      "start": {
        "time": {
          "timestamp": "2026-05-13T17:08:00+00:00"
        }
      },
      "end": {
        "time": {
          "timestamp": "2026-05-13T17:19:00+00:00"
        }
      }
    }
  }
}
```

---

## 6. Reschedule (Reschedule Booking)

Reschedule an existing appointment to a new slot.

### Endpoint

```
POST /appointment/reschedule/
```

### Request

```json
{
  "context": {
    "message_id": "81a44c90-9c8d-4b67-be3c-118dd0164061",
    "transaction_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1"
  },
  "message": {
    "order_id": "0fe564ae-9eb8-4fd6-a51a-90e6a60c8b72",
    "fulfillment_id": "7048156e-fefa-41a8-9f8b-7ff18f61d376",
    "note": "Rescheduled due to patient unavailability"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `context.message_id` | `string` | Yes | Unique message ID (UUID) |
| `context.transaction_id` | `string` | Yes | Transaction ID (UUID) |
| `message.order_id` | `string` | Yes | Existing booking order ID |
| `message.fulfillment_id` | `string` | Yes | New slot external ID |
| `message.note` | `string` | No | Reason for rescheduling |

### Response

```json
{
  "context": {
    "domain": "nic2004:85110",
    "country": "IND",
    "city": "234e81e4-a4c4-474c-a60e-a8eb5da162ba",
    "action": "reschedule",
    "core_version": "0.0.1",
    "message_id": "81a44c90-9c8d-4b67-be3c-118dd0164061",
    "transaction_id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1"
  },
  "message": {
    "order_id": "fd574d6a-2b5c-42d1-8ba6-578efe1f5bf7",
    "status": "booked",
    "provider": {
      "id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1",
      "descriptor": {
        "name": "Choudhry-Bhakta",
        "short_desc": "Odio eum quibusdam. Repellat impedit fugiat esse tenetur autem sint corporis.\nPariatur eum rem. Sequi repellendus natus animi."
      },
      "location": {
        "id": "488a430b-9c3a-4f79-a7bf-c9c7dadc01c1",
        "gps": "17.9823069999999987,-166.7245249999999999",
        "address": "08/795\nSachar, Bijapur-169669"
      }
    },
    "patient": {
      "id": "3b093cf8-d7c7-4a9c-9186-ebe5f15dec35",
      "name": "Priya",
      "gender": "female",
      "phone_number": "+917485658957",
      "date_of_birth": "2000-12-20",
      "address": "13-6-454/36/1, Hiranagar, Gudimalkapur, Asifnagar, Hyderabad, Telangana, IND - 500067"
    },
    "fulfillment": {
      "id": "7048156e-fefa-41a8-9f8b-7ff18f61d376",
      "type": "physical",
      "agent": {
        "id": "7a8377ff-ba7e-4cc5-a5f3-2610f338d0ff",
        "name": "Nandini Palla",
        "role": "",
        "departments": []
      },
      "start": {
        "time": {
          "timestamp": "2026-05-15T17:10:00+00:00"
        }
      },
      "end": {
        "time": {
          "timestamp": "2026-05-15T17:20:00+00:00"
        }
      }
    },
    "token": "GC - 3",
    "item": {
      "id": "5a8ce217-0373-44b1-ac43-006ae5a3fd52",
      "descriptor": {
        "name": "regular op",
        "code": "CONSULTATION"
      },
      "price": {
        "currency": "INR",
        "value": "0"
      },
      "fulfillment_id": "7048156e-fefa-41a8-9f8b-7ff18f61d376",
      "slot_type": "appointment",
      "slot_duration_minutes": 10
    },
    "quote": {
      "price": {
        "currency": "INR",
        "value": "0"
      },
      "breakup": []
    }
  }
}
```

---

## 7. Service Availability

List healthcare services available at facilities with optional filters. When multiple services are provided, only facilities that have **all** the requested services are returned.

### Endpoint

```
POST /service_availability/
```

### Request

```json
{
  "provider_id": "d682a4b6-b588-4320-9f6b-2541b96e949f",
  "pincode": "682030",
  "services": ["pathology", "cardiology"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider_id` | `string` | No | Facility external ID (UUID) |
| `pincode` | `string` or `integer` | No | Facility pincode |
| `services` | `string` or `array[string]` | No | Healthcare service name(s). Case-insensitive partial match. |

### Filter Behavior

| Filters Provided | Result |
|-----------------|--------|
| None | All facilities with all their services |
| `provider_id` only | All services for that facility |
| `pincode` only | All facilities in that pincode with their services |
| `services` only | Only facilities that have all the specified services |
| `pincode` + `services` | Facilities in that pincode that have all the specified services |
| `provider_id` + `services` | Matching services at that specific facility |

### Response

```json
{
  "providers": [
    {
      "id": "d682a4b6-b588-4320-9f6b-2541b96e949f",
      "descriptor": {
        "name": "Keonjhar Hospital",
        "short_desc": "",
        "phone": "+918888888888"
      },
      "location": {
        "id": "d682a4b6-b588-4320-9f6b-2541b96e949f",
        "gps": "",
        "address": "asd"
      },
      "services": [
        {
          "id": "88faefe9-4e92-4bb6-adc6-a520d5a68483",
          "name": "Cardiology",
          "managing_department": {
            "id": "81a44c90-9c8d-4b67-be3c-118dd0164061",
            "name": "Cardiology"
          }
        },
        {
          "id": "6a278cc1-5180-4c27-9980-5be8db6d21b0",
          "name": "Pathology",
          "managing_department": {
            "id": "3c6fd55c-af2d-4af5-8d91-125652209e0a",
            "name": "Pathology"
          }
        }
      ]
    }
  ]
}
```

---
