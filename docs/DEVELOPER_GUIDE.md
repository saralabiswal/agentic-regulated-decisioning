# Developer Guide

Author: Sarala Biswal

This guide walks through one end-to-end Playbook run and shows the API calls, request bodies, and representative responses. The sample uses the seeded insurance commercial-property Playbook.

Dynamic values such as UUIDs, timestamps, and latency change on every run. The example responses below preserve the real response shape while using representative values.

For implementation status and production hardening gaps, see `docs/planning/IMPLEMENTATION_STATUS.md`.

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

The repository currently includes 20 seeded YAML templates across insurance, lending, healthcare, and wealth workflows.

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
| 5 | `GET` | `/api/v1/playbook/{submission_id}/stream` | Stream stored layer and rule events as SSE |
| 6 | `GET` | `/api/v1/playbook/{submission_id}/results` | Fetch run summary, audit, rule events, layer events |
| 7 | `GET` | `/api/v1/playbook/{submission_id}/audit-record` | Fetch raw audit package |
| 8 | `GET` | `/api/v1/playbook/{submission_id}/report` | Fetch business and technical report package |
| 9 | `GET` | `/api/v1/playbook/history` | Fetch recent persisted Playbook runs |

## Code Flow

This section follows the same commercial-property sample through the application code.

```text
POST /api/v1/playbook/run
  api/routers/playbook.py::run_playbook
    _validate_content
      core/playbook_schema.py::parse_playbook_yaml
      domains/registry.py::DomainRegistry.get("insurance")
      domains/insurance/adapter.py::InsuranceAdapter.validate_submission
    platform/playbook/executor.py::PlaybookExecutor.run
      _merge_escalation
      _merge_governance
      _build_submission
      _emit_rule_events
      platform/orchestrator/graph.py::build_graph().ainvoke
        load_domain_adapter
        assemble_context
        run_agent_0
        apply_governance_0
          if escalation: route_to_human -> write_audit_trail
          else: run_agent_1
        apply_governance_1
          if escalation: route_to_human -> write_audit_trail
          else: run_agent_2
        apply_governance_2
          if escalation: route_to_human -> write_audit_trail
          else: write_audit_trail
      platform/playbook/history.py::write_run
```

### 1. API Entry And Validation

`api/main.py` mounts the Playbook router under `/api/v1`, so `/api/v1/playbook/run` enters `api/routers/playbook.py::run_playbook`.

`run_playbook` first calls `_validate_content`. Validation has two layers:

- `core/playbook_schema.py::parse_playbook_yaml` parses YAML and validates the typed Playbook contract with Pydantic.
- `domains/registry.py::DomainRegistry.get` resolves the selected domain adapter. For this sample, `domain.name: insurance` returns `InsuranceAdapter`.
- `domains/insurance/adapter.py::validate_submission` checks domain-specific required fields for `commercial_property`, such as `property_address`, `construction_type`, `year_built`, `total_insured_value`, `occupancy`, and `prior_claims`.

If validation has an error, the API returns HTTP `422`. Warnings remain visible but do not block execution.

### 2. Playbook Executor

After validation, `PlaybookExecutor.run` becomes the service-level entrypoint for the decision run.

The executor:

- Loads the domain adapter again from `DomainRegistry`.
- Merges default domain escalation thresholds with the Playbook rules in `_merge_escalation`.
- Merges jurisdiction governance with Playbook-specific controls in `_merge_governance`.
- Converts the Playbook into a canonical `SubmissionEvent` in `_build_submission`.
- Emits Playbook rule and L0-L9 layer events for `/stream`, `/results`, and `/report`.
- Invokes the LangGraph orchestrator with `build_graph().ainvoke(OrchestratorState(...))`.
- Persists the completed run summary through `platform/playbook/history.py::write_run`.

For this sample, `_build_submission` infers `case_value` from `total_insured_value: 4200000`. `_merge_governance` also adds a Playbook value-threshold review condition equivalent to `case_value > 1000000`.

### 3. Domain Adapter

The insurance adapter owns the domain-specific execution contract:

- `get_agent_sequence("commercial_property")` returns `["triage", "risk_scoring", "appetite_check"]`.
- `get_escalation_thresholds` provides default insurance review thresholds.
- `get_governance_rules("US_CA")` loads `domains/insurance/governance/US_CA.yaml`.
- `get_mcp_config` loads the context source configuration from `domains/insurance/mcp_config.yaml`.

The platform does not import insurance logic directly. It talks to the adapter through the shared domain protocol, and the orchestrator imports the selected domain's agent module only after the domain has been resolved.

### 4. Orchestrator Graph

`platform/orchestrator/graph.py::DecisionGraph` compiles the runtime graph.

The graph is compiled with this routing order. Conditional edges can route to human review before later agents run.

1. `load_domain_adapter` records the selected adapter id on the state.
2. `assemble_context` calls `platform/mcp/assembler.py::assemble` to build `UnifiedContext` from core, history, and external MCP sources.
3. `run_agent_0`, `run_agent_1`, and `run_agent_2` execute the domain agent sequence returned by the adapter when routing allows them to continue.
4. `apply_governance_0`, `apply_governance_1`, and `apply_governance_2` evaluate governance after each agent output.
5. `route_to_human` creates a workbench case when governance, confidence, value, or mandatory-review routing requires human review.
6. `write_audit_trail` appends the final reconstruction record.

### 5. Insurance Agents

`platform/orchestrator/nodes.py::run_named_agent` dynamically imports `domains.insurance.agents` and executes the named agent from the `AGENTS` map.

For insurance commercial-property submissions, the configured agent path is:

- `triage` classifies the submission using case type, value, occupancy, protection class, and context completeness.
- `risk_scoring` scores the risk while excluding prohibited jurisdictional factors.
- `appetite_check` converts the scored risk into an underwriting recommendation.

In this sample, the value-threshold rule triggers after `triage`, so the graph can route to human review before `risk_scoring` and `appetite_check` run. Lower-value cases that pass the first governance check continue through the remaining configured agents.

Each agent returns an `AgentOutput` with decision, confidence, evidence, flags, explanation, and processing time. The explanation is mandatory because audit and reviewer workflows depend on it.

### 6. Governance And Routing

`platform/governance/engine.py::GovernanceEngine.evaluate` applies governance to the current orchestrator state.

The engine:

- Loads jurisdiction rules from the domain governance YAML unless the Playbook executor supplied a merged override.
- Records every prohibited factor and escalation override that was applied.
- Verifies that agent outputs have explanations.
- Checks whether any evidence uses prohibited factors.
- Evaluates escalation conditions such as `case_value > 1000000`.

In the sample run, `case_value` is `4200000`, so the Playbook value-threshold condition is triggered. Governance can still pass from a prohibited-factor perspective, but the graph routes the case to human review because escalation was triggered.

### 7. Audit, Results, And Reports

When the graph reaches `write_audit_trail`, `platform/governance/audit_trail.py::AuditTrailWriter.write` creates an append-only `AuditRecord`.

The follow-up APIs read persisted and in-memory execution artifacts:

- `/results` calls `get_playbook_results`, which combines run history, audit records, rule events, and layer events.
- `/audit-record` returns the raw audit package from `AuditTrailWriter.get`.
- `/report` packages the same data into business and technical summaries.
- `/stream` emits the stored layer and rule events as server-sent events.

This is why the `submission_id` returned by `/run` is the key used by every later API call.

## Customization Guide

The codebase is designed so business behavior changes start in `domains/` and `static/playbook_templates/`, while platform behavior stays in `platform/` and `api/`.

| Change | Primary files | Notes |
|---|---|---|
| Add or edit a Playbook template | `static/playbook_templates/*.yaml` | Must satisfy `core/playbook_schema.py` and the selected domain adapter validation. |
| Add a case type to an existing domain | `core/playbook_schema.py`, `domains/<domain>/adapter.py`, `domains/<domain>/agents.py` | Update `VALID_CASE_TYPES`, adapter `supported_case_types`, validation fields, and agent sequencing if the case needs a different sequence. |
| Tune domain policy | `domains/<domain>/governance/*.yaml`, `domains/<domain>/adapter.py` | Governance YAML owns prohibited factors, disclosures, retention, and escalation overrides. Adapter thresholds own confidence/value/mandatory review defaults. |
| Tune specialist logic | `domains/<domain>/agents.py` | Agents must return `AgentOutput` with evidence, flags, confidence, processing time, and a non-empty explanation. |
| Configure real context systems | `.env`, `core/config.py`, `platform/mcp/connectors/real/__init__.py` | Real connectors use deployment-provided HTTP JSON URL templates. Secrets stay in environment variables, not code. |
| Add or train model families | `scripts/train_local_model.py`, `scripts/smoke_app_domain_models.py`, `platform/registry/` | Optional runtimes require the `app-models` extra; deterministic fallback keeps the app runnable without models. |
| Change UI workflow text or panels | `ui/src/App.tsx`, `ui/src/styles.css`, `ui/src/pages/*` | API contracts are typed in the React code and backed by FastAPI response models. |

### Customize Playbooks

A Playbook is a YAML contract parsed by `core/playbook_schema.py::parse_playbook_yaml`. The top-level sections are:

- `playbook`: name, version, creator, and description.
- `domain`: `name` and `case_type`.
- `jurisdiction`: currently `US_CA`, `US_TX`, `US_NY`, `US_FL`, or `federal`.
- `rules`: optional controls that can tighten thresholds or add mandatory review triggers.
- `submission`: domain-owned business input.

The platform deliberately merges Playbook rules conservatively:

- `confidence_threshold` can make review stricter, not weaker.
- `max_auto_decision_value` can lower the auto-decision ceiling, not raise it above the domain default.
- `mandatory_review_triggers` append to domain governance overrides.
- `prohibited_factors` append to jurisdiction policy.

After schema parsing, the selected adapter validates the `submission` fields. For example, lending `auto_loan` requires `annual_income`, `employment_type`, `years_employed`, `monthly_debt_obligations`, `requested_loan_amount`, `vehicle_year`, `vehicle_type`, `prior_derogatory_marks`, and `months_credit_history`.

### Customize An Existing Domain

Each domain adapter implements `domains/base.py::DomainAdapter`.

For an existing domain, the usual workflow is:

1. Update `supported_case_types` and `get_agent_sequence` in `domains/<domain>/adapter.py`.
2. Update `validate_submission` so Playbook uploads fail fast on missing or invalid business inputs.
3. Update `get_escalation_thresholds` when the domain review thresholds change.
4. Update or add governance YAML under `domains/<domain>/governance/`.
5. Update `domains/<domain>/agents.py` so each agent in the sequence can run and return a valid `AgentOutput`.
6. Add or update seeded templates under `static/playbook_templates/`.
7. Add tests in `tests/test_playbook_schema.py`, `tests/test_domain_agents.py`, or a domain-specific test.

Agent modules can expose either an `AGENTS` map whose objects implement `run(context, prior_outputs)`, or a module-level `run_agent(name, context, prior_outputs)` function. The orchestrator supports both. Insurance currently uses the `AGENTS` map style; lending, healthcare, and wealth use `run_agent`.

Keep these invariants intact:

- Platform and API modules must not import domain-specific policy logic directly.
- Public layer boundaries should use Pydantic models, not ad hoc dict contracts.
- `AgentOutput.explanation` is required and must be meaningful enough for audit and reviewer workflows.
- If an agent uses a factor prohibited by governance, governance should detect it through evidence fields.
- Human review should be triggered through confidence, flags, value thresholds, mandatory cases, or governance overrides, not through hidden platform branching.

### Add A New Domain

The current typed application supports four domain ids: `insurance`, `lending`, `healthcare`, and `wealth`. Adding a fifth domain is supported by the architecture, but it requires updating the typed allowlists as well as adding the plugin files.

Minimum code changes:

1. Add `domains/<new_domain>/adapter.py`, `agents.py`, and `governance/*.yaml`.
2. Implement the `DomainAdapter` protocol from `domains/base.py`.
3. Register the adapter in `domains/registry.py`.
4. Add the new domain id to `core/schemas.py::DomainId`.
5. Add its case types to `core/playbook_schema.py::VALID_CASE_TYPES`.
6. Add supported jurisdictions to `PlaybookJurisdiction` if the domain needs jurisdictions outside the current literals.
7. Add seeded Playbook templates under `static/playbook_templates/`.
8. Add tests proving the adapter validates, the Playbook parses, and the agents return valid outputs.

Run `pytest tests/test_domain_protocol.py -v` after registration. That test is the guardrail that the domain still plugs into the platform through the adapter contract.

### Customize Real MCP Connectors

The mock/local path is the default. In `APP_MODE=real`, core, history, and external context sources call URL templates configured through environment variables:

```text
APP_MODE=real
MCP_CORE_URL_TEMPLATE=https://core.example.com/{domain}/entities/{entity_id}
MCP_HISTORY_URL_TEMPLATE=https://history.example.com/{domain}/entities/{entity_id}/history
MCP_EXTERNAL_URL_TEMPLATE=https://external.example.com/{domain}/entities/{entity_id}/external
MCP_API_KEY=shared-token
```

Source-specific keys `MCP_CORE_API_KEY`, `MCP_HISTORY_API_KEY`, and `MCP_EXTERNAL_API_KEY` override `MCP_API_KEY`. Each connector must return a JSON object. The real connector client escapes `{domain}` and `{entity_id}`, adds a bearer token when configured, and raises a connector error if the endpoint is unavailable, returns non-2xx, invalid JSON, or a non-object payload.

Context assembly is intentionally tolerant. `platform/mcp/assembler.py` gathers the three sources and converts missing sources into `UnifiedContext.sources_missing`. If a Playbook upload has no core connector result, the raw Playbook submission becomes the core context so local business testing can still run.

### Customize Models

Model scoring is optional. The application runs without registered MLflow models because deterministic fallback scoring is always available.

Use these commands when you want model-backed smoke paths:

```bash
make train-model DOMAIN=insurance MODEL_TYPE=risk VERSION=local-1 STAGE=Staging FAMILY=sklearn
make train-domain-models
make smoke-app-domain-models
```

Supported `FAMILY` values are `sklearn`, `gradient_boosting`, `pyfunc`, and optional `xgboost`, `lightgbm`, `onnx`, `torch`, and `tensorflow`. Install optional runtime families with:

```bash
uv sync --extra app-models
```

The local synthetic data in `scripts/train_local_model.py` is for development and smoke testing. Replace it with governed production feature pipelines and model artifacts before using these paths for real decisioning.

### Customize Runtime And UI

Runtime behavior is environment-driven through `core/config.py` and surfaced through:

```text
GET  /api/v1/config
POST /api/v1/config/runtime
GET  /api/v1/streams/inspection
```

The runtime config API is intentionally process-local. It is useful for the UI Settings page and demos; it does not write `.env` files or secrets.

The UI shell is in `ui/src/App.tsx`, with CSS in `ui/src/styles.css` and page modules under `ui/src/pages/`. When changing UI behavior, keep API payload shapes aligned with the Pydantic response models in `api/routers/*.py`.

## Verification For Developers

Run these before committing implementation changes:

```bash
make lint
make typecheck
make test
npm --prefix ui run build
```

Useful focused checks:

```bash
pytest tests/test_domain_protocol.py -v
pytest tests/test_playbook_schema.py -v
pytest tests/test_domain_agents.py -v
pytest tests/test_real_mcp_connectors.py -v
```

For live infrastructure paths:

```bash
make docker-up
make migrate
make live-smoke
make docker-down
```

Keep `APP_MODE=mock` and `LLM_PROVIDER=mock` for isolated CI-style runs. Use `APP_MODE=local_sync` for local Playbook demos, and `APP_MODE=real` only when connector templates and live services are configured.
