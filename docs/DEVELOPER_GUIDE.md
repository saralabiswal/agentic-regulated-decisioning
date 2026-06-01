# Developer Guide

Author: Sarala Biswal

This guide walks through one end-to-end Playbook run and shows the API calls, request bodies, and representative responses. The sample uses the seeded insurance commercial-property Playbook.

Dynamic values such as UUIDs, timestamps, and latency change on every run. The example responses below preserve the real response shape while using representative values.

## Sample Use Case

Use case: commercial property underwriting for an office building in San Francisco.

Template file:

```text
static/playbook_templates/playbook_insurance_commercial_property.yaml
```

Business input:

```yaml
playbook:
  name: "Commercial Property Underwriting - San Francisco"
  version: "1.0"
  created_by: "Risk operations"
  description: "Mid-size office building submission for review."

domain:
  name: insurance
  case_type: commercial_property

jurisdiction:
  code: US_CA

rules:
  max_auto_decision_value: 1000000
  confidence_threshold: 0.75
  mandatory_review_triggers:
    - "prior_claims > 3"
  prohibited_factors:
    - credit_score

submission:
  property_address: "450 Market Street, San Francisco, CA 94105"
  construction_type: masonry
  year_built: 1991
  total_insured_value: 4200000
  occupancy: office
  square_footage: 28000
  number_of_stories: 8
  sprinkler_system: true
  prior_claims: 1
  prior_claims_total_value: 42000
  protection_class: 3
  distance_to_fire_station_miles: 1.2
  notes: "Tenant-occupied office building. Recently renovated."
```

Expected outcome: the run escalates to human review because the case value is above the automatic decision threshold.

## Start The API

From the repository root:

```bash
make dev
```

Default API base URL:

```text
http://127.0.0.1:8000
```

The Playbook APIs are mounted under:

```text
/api/v1/playbook
```

## Build A JSON Request Body

The validate and run APIs accept JSON with one field, `content`, where `content` is the full YAML string.

```bash
python -c "import json, pathlib; print(json.dumps({'content': pathlib.Path('static/playbook_templates/playbook_insurance_commercial_property.yaml').read_text()}))" > /tmp/playbook_payload.json
```

The generated request body has this shape:

```json
{
  "content": "playbook:\n  name: \"Commercial Property Underwriting - San Francisco\"\n  version: \"1.0\"\n..."
}
```

## API Call Sequence

### 1. List Available Templates

Request:

```bash
curl -s http://127.0.0.1:8000/api/v1/playbook/templates
```

Representative response:

```json
[
  {
    "name": "playbook_insurance_commercial_property.yaml",
    "size_bytes": 753
  },
  {
    "name": "playbook_lending_auto_loan.yaml",
    "size_bytes": 694
  }
]
```

### 2. Fetch The Selected Template

Request:

```bash
curl -s http://127.0.0.1:8000/api/v1/playbook/templates/playbook_insurance_commercial_property.yaml
```

Representative response:

```yaml
playbook:
  name: "Commercial Property Underwriting - San Francisco"
domain:
  name: insurance
  case_type: commercial_property
jurisdiction:
  code: US_CA
```

### 3. Validate The Playbook

Request:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/playbook/validate \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/playbook_payload.json
```

Representative response:

```json
{
  "valid": true,
  "messages": [],
  "playbook": {
    "playbook": {
      "name": "Commercial Property Underwriting - San Francisco",
      "version": "1.0",
      "created_by": "Risk operations",
      "description": "Mid-size office building submission for review."
    },
    "domain": {
      "name": "insurance",
      "case_type": "commercial_property"
    },
    "jurisdiction": {
      "code": "US_CA"
    },
    "rules": {
      "max_auto_decision_value": 1000000.0,
      "confidence_threshold": 0.75,
      "mandatory_review_triggers": [
        "prior_claims > 3"
      ],
      "prohibited_factors": [
        "credit_score"
      ]
    }
  }
}
```

If validation fails, `valid` is `false` and `messages` contains structured validation errors:

```json
{
  "severity": "error",
  "field": "domain.case_type",
  "message": "case_type is not valid for domain",
  "code": "value_error"
}
```

### 4. Run The Playbook

Request:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/playbook/run \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/playbook_payload.json
```

Representative response:

```json
{
  "submission_id": "72bde294-f424-4673-b5f1-9ada4554d116",
  "status": "completed"
}
```

Save `submission_id`; all follow-up calls use it.

### 5. Fetch Run Results

Request:

```bash
curl -s http://127.0.0.1:8000/api/v1/playbook/72bde294-f424-4673-b5f1-9ada4554d116/results
```

Representative response:

```json
{
  "run": {
    "playbook_run_id": "cd89e0bc-3100-44fd-a955-91ff759cbcd9",
    "submission_id": "72bde294-f424-4673-b5f1-9ada4554d116",
    "playbook_name": "Commercial Property Underwriting - San Francisco",
    "domain": "insurance",
    "case_type": "commercial_property",
    "jurisdiction": "US_CA",
    "final_decision": "ESCALATED",
    "total_latency_ms": 3899,
    "total_llm_cost": 0.0,
    "created_at": "2026-06-01T00:28:13.677848Z"
  },
  "audit_records": [
    {
      "audit_id": "4f6e7539-4507-4f72-98ab-ddd8ca5e62bc",
      "submission_id": "72bde294-f424-4673-b5f1-9ada4554d116",
      "domain": "insurance",
      "jurisdiction": "US_CA",
      "decision_type": "human_override",
      "final_decision": "ESCALATED",
      "governance_rules_applied": [
        "prohibited_factor:credit_score",
        "override:case_value > 1000000",
        "override:prior_claims > 3"
      ],
      "governance_passed": true,
      "human_reviewer": null
    }
  ],
  "rule_events": [
    {
      "layer": 9,
      "rule_source": "playbook",
      "rule_field": "prohibited_factors",
      "rule_value": "credit_score",
      "result": "factor_not_present",
      "display": "credit_score checked against submission and evidence."
    },
    {
      "layer": 9,
      "rule_source": "playbook",
      "rule_field": "mandatory_review_triggers",
      "rule_value": "prior_claims > 3",
      "result": "not_triggered",
      "display": "Playbook trigger 'prior_claims > 3' evaluated as not_triggered."
    }
  ],
  "layer_events": [
    {
      "layer": "L0",
      "name": "Intake",
      "status": "complete",
      "duration_ms": 4,
      "detail": "Playbook accepted"
    },
    {
      "layer": "L1",
      "name": "Stream",
      "status": "complete",
      "duration_ms": 8,
      "detail": "Local execution path"
    }
  ]
}
```

Important fields:

- `run.final_decision`: final platform outcome, `ESCALATED` for this sample.
- `audit_records`: append-only reconstruction data for decision audit.
- `rule_events`: Playbook and governance rule evaluations.
- `layer_events`: L0-L9 execution trace used by the UI.

### 6. Fetch Audit Package

Request:

```bash
curl -s http://127.0.0.1:8000/api/v1/playbook/72bde294-f424-4673-b5f1-9ada4554d116/audit-record
```

Representative response:

```json
{
  "submission_id": "72bde294-f424-4673-b5f1-9ada4554d116",
  "audit_records": [
    {
      "decision_type": "human_override",
      "final_decision": "ESCALATED",
      "governance_passed": true,
      "governance_rules_applied": [
        "prohibited_factor:credit_score",
        "override:case_value > 1000000"
      ]
    }
  ]
}
```

### 7. Fetch Report Package

Request:

```bash
curl -s http://127.0.0.1:8000/api/v1/playbook/72bde294-f424-4673-b5f1-9ada4554d116/report
```

Representative response:

```json
{
  "submission_id": "72bde294-f424-4673-b5f1-9ada4554d116",
  "business_summary": {
    "decision": "ESCALATED",
    "domain": "insurance",
    "case_type": "commercial_property",
    "jurisdiction": "US_CA"
  },
  "technical_summary": {
    "layer_events": [],
    "rule_events": [],
    "audit_records": []
  }
}
```

The real response includes full `layer_events`, `rule_events`, and `audit_records`; the example above shows the top-level report shape.

## Endpoint Summary

| Step | Method | Endpoint | Purpose |
|---|---|---|---|
| 1 | `GET` | `/api/v1/playbook/templates` | List seeded Playbook templates |
| 2 | `GET` | `/api/v1/playbook/templates/{name}` | Fetch YAML for one template |
| 3 | `POST` | `/api/v1/playbook/validate` | Validate YAML and domain submission rules |
| 4 | `POST` | `/api/v1/playbook/run` | Execute context assembly, agents, governance, audit |
| 5 | `GET` | `/api/v1/playbook/{submission_id}/results` | Fetch run summary, audit, rule events, layer events |
| 6 | `GET` | `/api/v1/playbook/{submission_id}/audit-record` | Fetch raw audit package |
| 7 | `GET` | `/api/v1/playbook/{submission_id}/report` | Fetch business and technical report package |
