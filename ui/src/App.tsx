// Author: Sarala Biswal
import React, { ChangeEvent, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  AlertTriangle,
  ArrowDownToLine,
  BookOpenCheck,
  BriefcaseBusiness,
  CheckCircle2,
  ClipboardList,
  Database,
  ExternalLink,
  FileText,
  GitBranch,
  Hospital,
  Landmark,
  Layers3,
  Loader2,
  Play,
  RefreshCw,
  Scale,
  ServerCog,
  SlidersHorizontal,
  WalletCards,
  XCircle,
} from 'lucide-react';
import './styles.css';

type DomainKey = 'insurance' | 'lending' | 'healthcare' | 'wealth';
type Persona = 'business' | 'technical' | 'compare';
type Page = 'workspace' | 'studio' | 'queue' | 'audit' | 'architecture' | 'settings' | 'operations';

const personaLabels: Record<Persona, string> = {
  business: 'Business',
  technical: 'Technical',
  compare: 'Side-by-side',
};

type ValidationMessage = {
  severity: 'error' | 'warning';
  field: string;
  message: string;
  code: string;
};

type ValidationResponse = {
  valid: boolean;
  messages: ValidationMessage[];
  playbook?: {
    playbook: { name: string; version: string };
    domain: { name: string; case_type: string };
    jurisdiction: { code: string };
    rules: {
      max_auto_decision_value?: number;
      confidence_threshold?: number;
      mandatory_review_triggers: string[];
      prohibited_factors: string[];
    };
    submission: Record<string, unknown>;
  };
};

type TemplateSummary = {
  name: string;
  size_bytes: number;
};

type PlaybookResult = {
  run: {
    submission_id: string;
    playbook_name: string;
    domain: string;
    case_type: string;
    jurisdiction: string;
    final_decision?: string;
    total_latency_ms?: number;
    total_llm_cost: number;
  } | null;
  audit_records: AuditRecordView[];
  rule_events: Array<{ display: string; result: string; rule_field: string }>;
  layer_events: Array<{ layer: string; name: string; status: string; duration_ms: number; detail: string }>;
};

type AuditRecordView = {
  audit_id: string;
  submission_id?: string;
  domain?: string;
  jurisdiction?: string;
  decision_type?: string;
  final_decision: string;
  agent_outputs?: Array<{ agent_type: string; decision: string; confidence: number; explanation: string }>;
  governance_rules_applied: string[];
  governance_passed: boolean;
  human_reviewer?: string | null;
  created_at?: string;
};

type WorkbenchCase = {
  case_id: string;
  submission: {
    submission_id: string;
    domain: string;
    jurisdiction: string;
    case_type: string;
    source_channel?: string;
    received_at?: string;
  };
  context?: {
    sources_available: string[];
    sources_missing: string[];
    context_confidence: string;
  };
  agent_outputs: Array<{
    agent_type: string;
    decision: string;
    confidence: number;
    explanation: string;
    flags?: string[];
    processing_ms?: number;
    evidence?: Array<{ source: string; field: string; value: unknown; confidence: number }>;
  }>;
  agent_recommendation: string;
  confidence: number;
  escalation_reason: string;
  assigned_to?: string | null;
  status: string;
  human_decision?: string | null;
  human_notes?: string | null;
  created_at?: string;
  decided_at?: string | null;
};

type AnalyticsSummary = {
  total_submissions: number;
  auto_decisions: number;
  escalations: number;
  escalation_rate: number;
  avg_confidence: number;
  decisions_by_outcome: Record<string, number>;
};

type HealthPayload = {
  status: string;
  checks: Record<string, string>;
};

type ModelVersion = {
  model_name: string;
  domain: string;
  model_type: string;
  version: string;
  stage: string;
};

type RuntimeConfigPayload = {
  app_mode?: 'mock' | 'real' | 'local_sync';
  llm_provider?: string;
  llm_model?: string;
};

type RuntimeMode = NonNullable<RuntimeConfigPayload['app_mode']>;

type RuntimeConfig = {
  app_mode: string;
  redis_url: string | null;
  database_url: string;
  mlflow_tracking_uri: string;
  jaeger_endpoint: string;
  llm_provider: string;
  llm_model: string;
  llm_base_url: string;
  ollama_base_url: string;
  ollama_model: string;
  openai_model: string;
  anthropic_model: string;
  default_domain: string;
  default_jurisdiction: string;
  llm_provider_status: {
    selected: string;
    openai_configured: boolean;
    anthropic_configured: boolean;
    custom_configured: boolean;
    ollama_configured: boolean;
  };
  effective_llm_provider: {
    provider: string;
    model: string;
    enabled: boolean;
    reason: string;
    api_base: string | null;
  };
  runtime_overrides: Record<string, string>;
};

type StreamInspection = {
  backend: 'memory' | 'redis' | 'local_sync';
  mode: string;
  stream_name: string;
  consumer_group: string;
  status: string;
  input_count: number;
  pending_count: number;
  dlq_count: number;
  recent_inputs: Array<{
    message_id: string;
    submission_id: string;
    domain: string;
    case_type: string;
    source_channel: string;
    received_at: string;
    parse_error?: string | null;
  }>;
  output_note: string;
};

type UiNotice = {
  severity: 'ok' | 'warning' | 'error';
  message: string;
};

type WorkspaceOutcome = {
  action: string;
  status: string;
  detail: string;
  stage: number;
  severity: 'ok' | 'warning';
  updatedAt: string;
};

type DomainConfig = {
  key: DomainKey;
  mark: string;
  label: string;
  subtitle: string;
  workspace: string;
  queue: string;
  title: string;
  summary: string;
  caseType: string;
  jurisdiction: string;
  playbook: string;
  outcome: string;
  outcomeTag: string;
  metricOne: [string, string];
  metricTwo: [string, string];
  flow: Array<[string, string, string]>;
  facts: Array<[string, string]>;
  actions: string[];
  playbookBlocks: Array<[string, string]>;
  simulation: Array<[string, string, string]>;
};

type ArchitectureLayer = {
  id: string;
  name: string;
  short: string;
  owner: string;
  output: string;
  summary: string;
  business: string;
  technical: string;
  businessBullets: string[];
  technicalBullets: string[];
  evidence: Array<[string, string, string]>;
};

type ArchitectureStoryNode = {
  title: string;
  business: string;
  technical: string;
  layers: string[];
};

const fallbackTemplates: Record<DomainKey, string> = {
  insurance: `playbook:
  name: "Commercial Property Underwriting - San Francisco"
  version: "1.0"
  created_by: "Risk operations"

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
  prior_claims: 1
  protection_class: 3
`,
  lending: `playbook:
  name: "Auto Loan Conditional Approval"
  version: "1.0"
  created_by: "Credit operations"

domain:
  name: lending
  case_type: auto_loan

jurisdiction:
  code: US_NY

rules:
  max_auto_decision_value: 50000
  confidence_threshold: 0.78
  mandatory_review_triggers:
    - "debt_to_income > 0.45"
  prohibited_factors:
    - protected_class

submission:
  annual_income: 85000
  employment_type: salaried
  years_employed: 4
  monthly_debt_obligations: 1200
  requested_loan_amount: 38000
  vehicle_year: 2024
  vehicle_type: suv
  prior_derogatory_marks: 0
  months_credit_history: 84
`,
  healthcare: `playbook:
  name: "Imaging Prior Authorization"
  version: "1.0"
  created_by: "Clinical operations"

domain:
  name: healthcare
  case_type: prior_auth_imaging

jurisdiction:
  code: US_CA

rules:
  max_auto_decision_value: 0
  confidence_threshold: 0.82
  mandatory_review_triggers:
    - "criteria_missing > 0"
  prohibited_factors:
    - unrelated_demographic_data

submission:
  procedure_code: "72148"
  procedure_description: "MRI lumbar spine"
  diagnosis_code: "M54.50"
  diagnosis_description: "Low back pain"
  conservative_treatment_tried: true
  conservative_treatment_duration_weeks: 6
  ordering_provider_specialty: orthopedics
  patient_age: 47
  symptom_duration_weeks: 8
  prior_imaging_same_region: false
`,
  wealth: `playbook:
  name: "Annuity Suitability Review"
  version: "1.0"
  created_by: "Wealth compliance"

domain:
  name: wealth
  case_type: annuity_recommendation

jurisdiction:
  code: US_NY

rules:
  max_auto_decision_value: 250000
  confidence_threshold: 0.8
  mandatory_review_triggers:
    - "liquidity_need == high"
  prohibited_factors:
    - unsupported_risk_assumption

submission:
  client_age: 59
  investment_objective: income
  risk_tolerance: moderate
  liquid_net_worth: 780000
  annual_income: 145000
  investment_amount: 260000
  liquidity_needs: medium
`,
};

const domainConfigs: Record<DomainKey, DomainConfig> = {
  insurance: {
    key: 'insurance',
    mark: 'IN',
    label: 'Insurance',
    subtitle: 'Insurance decision cockpit',
    workspace: 'Decision Cockpit',
    queue: 'Referral Queue',
    title: 'Insurance Decision Cockpit',
    summary:
      'Current insurance decision status, evidence posture, governance result, and next action.',
    caseType: 'Commercial Property',
    jurisdiction: 'US_CA',
    playbook: 'Property Underwriting v1.0',
    outcome: 'Refer for underwriter review',
    outcomeTag: 'Escalated',
    metricOne: ['Confidence', '71%'],
    metricTwo: ['Exposure', '$4.2M'],
    flow: [
      ['Submission', 'Case created', 'Property details are captured and jurisdiction is assigned.'],
      ['Enrichment', 'Evidence added', 'Claims, history, and external risk context are attached.'],
      ['Risk Assessment', 'Agents scored', 'Specialist agents evaluate risk and recommendation.'],
      ['Governance', 'Rules applied', 'Underwriting policy determines whether review is required.'],
      ['Underwriter Review', 'Referral routed', 'A reviewer receives the case packet and evidence.'],
      ['Decision Package', 'Audit ready', 'Report, audit record, and trace package are ready.'],
    ],
    facts: [
      ['Submission', 'sub_7ad4c219'],
      ['Primary reason', 'Exposure threshold'],
      ['Reviewer role', 'Risk manager'],
      ['Audit ID', 'aud_4f91a802'],
    ],
    actions: ['Open referral case', 'Download decision report', 'Download audit package'],
    playbookBlocks: [
      ['Input', 'Address, occupancy, total insured value, prior claims'],
      ['Rules', 'Auto-decision limit and prohibited factors'],
      ['Context', 'Claims, history, and external risk indicators'],
      ['Agents', 'Triage, risk scoring, and recommendation'],
      ['Governance', 'Referral gate and audit retention'],
    ],
    simulation: [
      ['Referral rate', '18%', '24%'],
      ['Auto approvals', '62%', '55%'],
      ['Avg confidence', '78%', '81%'],
      ['Governance findings', '4%', '3%'],
    ],
  },
  lending: {
    key: 'lending',
    mark: 'LN',
    label: 'Lending',
    subtitle: 'Lending decision cockpit',
    workspace: 'Decision Cockpit',
    queue: 'Loan Review Queue',
    title: 'Lending Decision Cockpit',
    summary:
      'Current lending decision status, applicant evidence, compliance posture, and next action.',
    caseType: 'Auto Loan',
    jurisdiction: 'US_NY',
    playbook: 'Credit Policy v3.2',
    outcome: 'Conditional approval',
    outcomeTag: 'Conditions',
    metricOne: ['Confidence', '83%'],
    metricTwo: ['Amount', '$38K'],
    flow: [
      ['Application', 'Captured', 'Applicant, product, requested amount, and jurisdiction are normalized.'],
      ['Eligibility', 'Checked', 'Product rules and hard-stop checks run before scoring.'],
      ['Credit Risk', 'Scored', 'Credit and risk agents evaluate the applicant profile.'],
      ['Affordability', 'Assessed', 'Debt-to-income and repayment capacity are checked.'],
      ['Compliance', 'Reviewed', 'Fair-lending and notice rules wrap the decision.'],
      ['Decision Notice', 'Ready', 'Decision reasons and conditions are ready for the applicant.'],
    ],
    facts: [
      ['Application', 'loan_app_2301'],
      ['Primary reason', 'Income verification'],
      ['Reviewer role', 'Loan officer'],
      ['Audit ID', 'aud_9c12e477'],
    ],
    actions: ['Open condition review', 'Download decision notice', 'Download audit package'],
    playbookBlocks: [
      ['Input', 'Applicant, vehicle, amount, affordability'],
      ['Rules', 'Eligibility and hard-stop checks'],
      ['Context', 'Credit and repayment evidence'],
      ['Agents', 'Credit risk and affordability recommendation'],
      ['Governance', 'Fair-lending, notice, and audit rules'],
    ],
    simulation: [
      ['Conditional approvals', '31%', '28%'],
      ['Manual review', '14%', '11%'],
      ['Declines', '9%', '10%'],
      ['Notice coverage', '100%', '100%'],
    ],
  },
  healthcare: {
    key: 'healthcare',
    mark: 'HC',
    label: 'Healthcare',
    subtitle: 'Healthcare determination cockpit',
    workspace: 'Decision Cockpit',
    queue: 'Clinical Review Queue',
    title: 'Healthcare Decision Cockpit',
    summary:
      'Current healthcare determination status, clinical evidence, review posture, and next action.',
    caseType: 'Prior Authorization',
    jurisdiction: 'US_CA',
    playbook: 'Clinical Criteria v2.5',
    outcome: 'Needs clinical review',
    outcomeTag: 'Clinical review',
    metricOne: ['Criteria match', '64%'],
    metricTwo: ['SLA', '18h'],
    flow: [
      ['Request', 'Received', 'Service, diagnosis, provider, and member context are captured.'],
      ['Clinical Intake', 'Normalized', 'Clinical notes, benefits, history, and policy criteria are assembled.'],
      ['Criteria', 'Matched', 'Medical criteria are matched, missing, or marked inconclusive.'],
      ['Medical Necessity', 'Assessed', 'Clinical agents assess evidence sufficiency and necessity.'],
      ['Reviewer Decision', 'Routed', 'The case is routed with gaps and criteria references.'],
      ['Determination', 'Ready', 'Determination notice and appeal-ready audit package are prepared.'],
    ],
    facts: [
      ['Authorization', 'PA-1187'],
      ['Primary reason', 'Criteria gap'],
      ['Reviewer role', 'Nurse reviewer'],
      ['Audit ID', 'aud_21ca0b44'],
    ],
    actions: ['Open clinical review', 'Download determination', 'Download audit package'],
    playbookBlocks: [
      ['Input', 'Service, diagnosis, member, provider'],
      ['Rules', 'Clinical criteria and benefit policy'],
      ['Context', 'Clinical packet and utilization history'],
      ['Agents', 'Evidence sufficiency and medical necessity'],
      ['Governance', 'Determination notice and appeal audit'],
    ],
    simulation: [
      ['Auto determinations', '42%', '48%'],
      ['Clinical review', '39%', '33%'],
      ['Info requests', '12%', '10%'],
      ['SLA risk', '7%', '5%'],
    ],
  },
  wealth: {
    key: 'wealth',
    mark: 'WL',
    label: 'Wealth',
    subtitle: 'Wealth suitability cockpit',
    workspace: 'Decision Cockpit',
    queue: 'Advisor Review Queue',
    title: 'Wealth Decision Cockpit',
    summary:
      'Current wealth recommendation status, suitability evidence, disclosure posture, and next action.',
    caseType: 'Suitability Check',
    jurisdiction: 'US_NY',
    playbook: 'Product Policy v1.8',
    outcome: 'Advisor review required',
    outcomeTag: 'Review',
    metricOne: ['Fit score', '76%'],
    metricTwo: ['Risk band', 'Moderate'],
    flow: [
      ['Client Profile', 'Captured', 'Goals, horizon, risk tolerance, and liquidity needs are normalized.'],
      ['Suitability', 'Checked', 'Client needs and constraints are evaluated against policy.'],
      ['Product Fit', 'Assessed', 'Suitability and product agents assess recommendation fit.'],
      ['Disclosure', 'Generated', 'Required disclosure language is attached to the case.'],
      ['Advisor Review', 'Routed', 'Advisor gets recommendation, checklist, and evidence.'],
      ['Compliance Archive', 'Ready', 'Recommendation, disclosure, and advisor action are archived.'],
    ],
    facts: [
      ['Client', 'client_8821'],
      ['Primary reason', 'Disclosure required'],
      ['Reviewer role', 'Advisor'],
      ['Audit ID', 'aud_f88b7201'],
    ],
    actions: ['Open advisor review', 'Download suitability report', 'Download audit package'],
    playbookBlocks: [
      ['Input', 'Client profile, risk, liquidity, objective'],
      ['Rules', 'Suitability constraints and disclosure policy'],
      ['Context', 'Client history and product data'],
      ['Agents', 'Suitability and product-fit assessment'],
      ['Governance', 'Disclosures and compliance archive'],
    ],
    simulation: [
      ['Advisor reviews', '22%', '19%'],
      ['Auto suitable', '51%', '56%'],
      ['Disclosure rate', '34%', '31%'],
      ['Override rate', '6%', '5%'],
    ],
  },
};

const platformLayers = [
  ['L0', 'Intake', 'Playbook parsed and validated'],
  ['L1', 'Stream', 'Submission event accepted'],
  ['L2', 'Orchestrator', 'Domain adapter selected'],
  ['L3', 'Agents', 'Specialists executed'],
  ['L4', 'Context', 'MCP sources assembled'],
  ['L5', 'Review', 'Human route evaluated'],
  ['L6', 'Data', 'Records persisted'],
  ['L7', 'Registry', 'Model version captured'],
  ['L8', 'Telemetry', 'Cost and latency recorded'],
  ['L9', 'Governance', 'Rules and audit sealed'],
];

const architectureLayers: ArchitectureLayer[] = [
  {
    id: 'L0',
    name: 'Submission intake',
    short: 'Case captured',
    owner: 'Channel',
    output: 'SubmissionEvent',
    summary: 'A domain request becomes a typed case with jurisdiction, case type, and playbook metadata.',
    business: 'The user sees a familiar case opening flow. The platform captures the request without exposing backend internals.',
    technical: 'The API validates the uploaded playbook and emits a typed submission event. No raw dictionaries cross the boundary.',
    businessBullets: ['Domain and jurisdiction are explicit.', 'The uploaded policy asset is visible.', 'The case can be traced from the first click.'],
    technicalBullets: ['Pydantic request and response models protect the boundary.', 'Validation runs before orchestration.', 'The event contains a stable submission id.'],
    evidence: [['Input', 'Playbook YAML', 'Schema-valid policy and submission data'], ['Guardrail', 'Naming rules', 'Generic terms only'], ['Trace', 'Run id', 'Created before execution']],
  },
  {
    id: 'L1',
    name: 'Async event stream',
    short: 'Work accepted',
    owner: 'Runtime',
    output: 'Stream position',
    summary: 'The accepted submission is queued so execution can retry, scale, and remain observable.',
    business: 'The case is now in progress. Users do not wait on a fragile synchronous chain.',
    technical: 'The runtime uses the configured queue path. Redis can be enabled locally, while the mock path remains the default.',
    businessBullets: ['The request is accepted quickly.', 'Retries do not create duplicate business cases.', 'Failures can be surfaced as recoverable work.'],
    technicalBullets: ['Queue provider is config-gated.', 'Messages carry typed payloads.', 'Dead-letter behavior preserves failed work for review.'],
    evidence: [['Queue', 'Accepted', 'Submission entered execution'], ['Retry', 'Available', 'Runtime can replay safe steps'], ['Status', 'Observable', 'Layer event is recorded']],
  },
  {
    id: 'L2',
    name: 'Domain orchestrator',
    short: 'Domain selected',
    owner: 'Decision engine',
    output: 'Agent sequence',
    summary: 'The orchestrator selects the domain adapter and builds the execution plan for the chosen case type.',
    business: 'The same workbench supports multiple regulated workflows without mixing their business rules.',
    technical: 'Domain-specific code stays inside domains. The shared orchestrator only deals in typed contracts.',
    businessBullets: ['Insurance, lending, healthcare, and wealth flows remain separate.', 'The selected case type controls the next steps.', 'Shared platform services stay consistent.'],
    technicalBullets: ['Adapter selection uses domain metadata.', 'Domain logic is isolated under domains.', 'The orchestrator returns a typed plan.'],
    evidence: [['Adapter', 'Selected', 'Domain and case type matched'], ['Plan', 'Sequenced', 'Specialist agents ordered'], ['Boundary', 'Enforced', 'No domain rules in shared runtime']],
  },
  {
    id: 'L3',
    name: 'Specialist agents',
    short: 'Recommendation built',
    owner: 'Agent runtime',
    output: 'AgentOutput',
    summary: 'Specialist agents evaluate the case and return recommendation, confidence, flags, evidence, and explanation.',
    business: 'The recommendation is expressed as an action the reviewer understands, with reasons attached.',
    technical: 'Every agent returns an AgentOutput, and explanation is required. Mock execution is default; real LLMs are opt-in by environment.',
    businessBullets: ['The decision is not a black box.', 'Confidence and reasons are visible.', 'Escalation is tied to explicit evidence.'],
    technicalBullets: ['AgentOutput explanation is never optional.', 'LLM provider selection is configuration-driven.', 'Mock connectors remain the default path.'],
    evidence: [['Output', 'AgentOutput', 'Decision, confidence, flags, explanation'], ['Mode', 'Mock default', 'Real providers require keys'], ['Evidence', 'Linked', 'Agent reasons reference available context']],
  },
  {
    id: 'L4',
    name: 'Context abstraction',
    short: 'Evidence assembled',
    owner: 'Context tier',
    output: 'UnifiedContext',
    summary: 'Internal, historical, external, and document evidence are normalized into one context view.',
    business: 'Reviewers see which evidence was available and which evidence influenced the decision.',
    technical: 'Connector paths are behind provider interfaces. Real external systems stay opt-in through configuration.',
    businessBullets: ['Evidence availability is visible.', 'Missing inputs can trigger review.', 'The same story is used in the report.'],
    technicalBullets: ['Connector implementations return typed models.', 'Provider choice is environment-controlled.', 'Context records are attached to the run trace.'],
    evidence: [['Core data', 'Available', 'Case and policy facts'], ['History', 'Attached', 'Prior activity and outcomes'], ['External', 'Config-gated', 'Only used when enabled']],
  },
  {
    id: 'L5',
    name: 'Human review',
    short: 'Action routed',
    owner: 'Reviewer',
    output: 'WorkbenchCase',
    summary: 'Escalated cases are routed to the right queue with reasons, evidence, and reviewer actions.',
    business: 'The user gets a clear next action instead of a static dashboard.',
    technical: 'A WorkbenchCase captures reviewer state. Human decisions append records rather than rewriting prior decisions.',
    businessBullets: ['Open, confirm, override, or request information.', 'Each action says what happens next.', 'Reviewer notes become part of the case story.'],
    technicalBullets: ['Reviewer state is typed.', 'Actions append audit entries.', 'Prior run records are not updated or deleted.'],
    evidence: [['Queue', 'Routed', 'Reviewer receives the case'], ['Actions', 'Explicit', 'Outcome-based buttons'], ['Audit', 'Append-only', 'Human action adds a new record']],
  },
  {
    id: 'L6',
    name: 'Data platform',
    short: 'Records persisted',
    owner: 'Persistence',
    output: 'Analytics record',
    summary: 'Decision, audit, review, and analytics records are stored for reconstruction and reporting.',
    business: 'Leaders can monitor referral rates, confidence, outcomes, and policy changes without reading raw traces.',
    technical: 'PostgreSQL stores canonical records, Redis supports runtime flow, and local paths work without managed services.',
    businessBullets: ['Metrics are tied to real runs.', 'Reports can be filtered by domain.', 'Audit history remains durable.'],
    technicalBullets: ['Database provider is configured by URL.', 'Audit records are append-only.', 'Analytics views read from persisted run data.'],
    evidence: [['Store', 'PostgreSQL', 'Canonical decision records'], ['Cache', 'Redis', 'Optional local service'], ['Analytics', 'Summary', 'Outcome and confidence metrics']],
  },
  {
    id: 'L7',
    name: 'Model registry',
    short: 'Model version captured',
    owner: 'Model operations',
    output: 'ScoringResult',
    summary: 'ML models and scoring versions are captured so every decision can be explained later.',
    business: 'The report can say which model family and version supported the recommendation.',
    technical: 'MLflow can run locally. Scoring can use open-source model artifacts such as scikit-learn, PyTorch, TensorFlow, or ONNX paths.',
    businessBullets: ['Model version is part of the decision package.', 'Fallback scoring is explicit.', 'Changes are visible before promotion.'],
    technicalBullets: ['Tracking URI controls local or remote registry.', 'Model metadata is recorded with the run.', 'Open-source runtimes can be loaded through adapters.'],
    evidence: [['Registry', 'MLflow', 'Local service supported'], ['Runtime', 'Open-source', 'Provider selected by config'], ['Version', 'Captured', 'Scoring metadata in trace']],
  },
  {
    id: 'L8',
    name: 'Observability',
    short: 'Runtime measured',
    owner: 'Operations',
    output: 'Telemetry event',
    summary: 'Latency, cost, service health, and execution events are exposed to operators.',
    business: 'Operational risk is visible: what ran, how long it took, and whether dependencies are healthy.',
    technical: 'Layer events and health checks make runtime behavior inspectable without reading logs first.',
    businessBullets: ['Run health is visible.', 'Latency and cost can be monitored.', 'Broken dependencies surface as status.'],
    technicalBullets: ['Health endpoint reports provider checks.', 'Layer events include duration and status.', 'Runtime mode is shown in Operations.'],
    evidence: [['Health', 'Reported', 'Backend and provider checks'], ['Events', 'Timed', 'Layer durations captured'], ['Cost', 'Tracked', 'LLM spend recorded when applicable']],
  },
  {
    id: 'L9',
    name: 'Governance band',
    short: 'Audit sealed',
    owner: 'Governance',
    output: 'AuditRecord',
    summary: 'Rules, prohibited factors, review triggers, and decision explanations are sealed into an audit package.',
    business: 'The organization can reconstruct why a decision happened and what policy was applied.',
    technical: 'Governance creates append-only audit records. Reports are generated from typed outputs and persisted events.',
    businessBullets: ['Review triggers are visible.', 'Prohibited factors are checked.', 'The decision package is regulator-ready.'],
    technicalBullets: ['Audit records are append-only.', 'Governance rules are stored with the run.', 'Report generation reads typed records.'],
    evidence: [['Rules', 'Applied', 'Policy controls evaluated'], ['Record', 'Sealed', 'Audit payload available'], ['Report', 'Ready', 'Decision reconstruction generated']],
  },
];

const architectureStoryNodes: ArchitectureStoryNode[] = [
  {
    title: 'Open case',
    business: 'A regulated request enters the workbench with domain, jurisdiction, and policy context.',
    technical: 'Typed intake validates the playbook and emits the first platform event.',
    layers: ['L0'],
  },
  {
    title: 'Accept work',
    business: 'The case is accepted and can progress without forcing the user to wait on every backend step.',
    technical: 'The stream path carries a typed message through the configured runtime.',
    layers: ['L1'],
  },
  {
    title: 'Build decision',
    business: 'The platform selects the right domain flow, assembles evidence, and produces a recommendation.',
    technical: 'Domain adapters, context connectors, agents, and model metadata produce typed outputs.',
    layers: ['L2', 'L3', 'L4', 'L7'],
  },
  {
    title: 'Govern action',
    business: 'Policy controls decide whether the recommendation can proceed or needs human review.',
    technical: 'Governance rules evaluate review triggers, prohibited factors, and explanation requirements.',
    layers: ['L5', 'L9'],
  },
  {
    title: 'Operate and prove',
    business: 'Reviewers and operators get the queue, report, health, and audit package needed to act.',
    technical: 'Records, telemetry, stream inspection, and audit data make the run reconstructable.',
    layers: ['L6', 'L8', 'L9'],
  },
];

const domainIcons: Record<DomainKey, React.ComponentType<{ size?: number }>> = {
  insurance: BriefcaseBusiness,
  lending: Landmark,
  healthcare: Hospital,
  wealth: WalletCards,
};

/**
 * Merge conditional class names without carrying falsey values into markup.
 */
function classNames(values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ');
}

/**
 * Convert seeded Playbook filenames into readable menu labels.
 */
function formatTemplateName(name: string) {
  return name
    .replace('playbook_', '')
    .replace('.yaml', '')
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

/**
 * Build the initial domain-specific action card before a Playbook has run.
 */
function initialWorkspaceOutcome(domain: DomainConfig): WorkspaceOutcome {
  return {
    action: 'Start decision flow',
    status: 'No run yet',
    detail: `Select a ${domain.label.toLowerCase()} Playbook template or upload YAML to create the first decision run.`,
    stage: 0,
    severity: 'ok',
    updatedAt: 'Start here',
  };
}

/**
 * Fetch JSON from the API and surface HTTP errors with response body details.
 */
async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body || url}`);
  }
  return (await response.json()) as T;
}

/**
 * Fetch text payloads such as seeded YAML templates.
 */
async function readText(url: string): Promise<string> {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body || url}`);
  }
  return response.text();
}

/**
 * Download a JSON API response through a temporary browser object URL.
 */
async function downloadJsonFile(url: string, filename: string) {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body || url}`);
  }
  const blob = await response.blob();
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(href);
}

/**
 * Main enterprise workbench shell.
 *
 * Owns shared runtime state for domain selection, persona view, Playbook execution,
 * reviewer queue actions, audit reports, architecture walkthrough, and settings.
 */
function App() {
  const [domainKey, setDomainKey] = useState<DomainKey>('insurance');
  const [persona, setPersona] = useState<Persona>(() => {
    return (localStorage.getItem('persona') as Persona | null) || 'compare';
  });
  const [page, setPage] = useState<Page>('workspace');
  const [selectedStage, setSelectedStage] = useState(0);
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [content, setContent] = useState(fallbackTemplates.insurance);
  const [playbookAssetSelected, setPlaybookAssetSelected] = useState(false);
  const [validation, setValidation] = useState<ValidationResponse | null>(null);
  const [result, setResult] = useState<PlaybookResult | null>(null);
  const [cases, setCases] = useState<WorkbenchCase[]>([]);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [runtimeConfig, setRuntimeConfig] = useState<RuntimeConfig | null>(null);
  const [streamInspection, setStreamInspection] = useState<StreamInspection | null>(null);
  const [notice, setNotice] = useState<UiNotice | null>(null);
  const [workspaceOutcome, setWorkspaceOutcome] = useState<WorkspaceOutcome>(() => initialWorkspaceOutcome(domainConfigs.insurance));
  const [isBusy, setIsBusy] = useState(false);

  const domain = domainConfigs[domainKey];
  const Icon = domainIcons[domainKey];
  const filteredTemplates = useMemo(
    () => templates.filter((template) => template.name.includes(domainKey)),
    [domainKey, templates],
  );

  useEffect(() => {
    localStorage.setItem('persona', persona);
    document.body.dataset.persona = persona;
  }, [persona]);

  useEffect(() => {
    readJson<TemplateSummary[]>('/api/v1/playbook/templates')
      .then(setTemplates)
      .catch((error: Error) => {
        setNotice({ severity: 'error', message: `Templates could not load. ${error.message}` });
      });
    refreshPlatformData();
    const timer = window.setInterval(refreshPlatformData, 30000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    setContent(fallbackTemplates[domainKey]);
    setPlaybookAssetSelected(false);
    setValidation(null);
    setResult(null);
    setSelectedStage(0);
    setWorkspaceOutcome(initialWorkspaceOutcome(domainConfigs[domainKey]));
    setNotice({ severity: 'ok', message: `${domain.label} decision cockpit selected.` });
  }, [domainKey, domain.label]);

  async function refreshPlatformData() {
    // Refresh low-risk dashboard data in parallel so page navigation stays responsive.
    const requests = await Promise.allSettled([
      readJson<WorkbenchCase[]>('/api/v1/workbench/cases?limit=20'),
      readJson<AnalyticsSummary>('/api/v1/analytics/summary'),
      readJson<HealthPayload>('/health'),
      readJson<ModelVersion[]>('/api/v1/registry/models'),
      readJson<RuntimeConfig>('/api/v1/config'),
      readJson<StreamInspection>(`/api/v1/streams/inspection?domain=${domainKey}&limit=8`),
    ]);
    if (requests[0].status === 'fulfilled') setCases(requests[0].value);
    if (requests[1].status === 'fulfilled') setSummary(requests[1].value);
    if (requests[2].status === 'fulfilled') setHealth(requests[2].value);
    if (requests[3].status === 'fulfilled') setModels(requests[3].value);
    if (requests[4].status === 'fulfilled') setRuntimeConfig(requests[4].value);
    if (requests[5].status === 'fulfilled') setStreamInspection(requests[5].value);
  }

  async function updateRuntimeSettings(payload: RuntimeConfigPayload) {
    setIsBusy(true);
    setNotice(null);
    try {
      await readJson('/api/v1/config/runtime', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const config = await readJson<RuntimeConfig>('/api/v1/config');
      const healthPayload = await readJson<HealthPayload>('/health');
      setRuntimeConfig(config);
      setHealth(healthPayload);
      setNotice({ severity: 'ok', message: 'Runtime settings applied for this process.' });
    } catch (error) {
      setNotice({ severity: 'error', message: `Settings update failed. ${(error as Error).message}` });
    } finally {
      setIsBusy(false);
    }
  }

  async function decideWorkbenchCase(caseId: string, decision: string, notes: string) {
    setIsBusy(true);
    setNotice(null);
    try {
      const response = await readJson<{ audit_trail_id: string }>(`/api/v1/workbench/cases/${caseId}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          notes,
          reviewer_id: 'reviewer.local',
        }),
      });
      await refreshPlatformData();
      setNotice({ severity: 'ok', message: `Reviewer action appended to audit ${response.audit_trail_id}.` });
    } catch (error) {
      setNotice({ severity: 'error', message: `Reviewer action failed. ${(error as Error).message}` });
      throw error;
    } finally {
      setIsBusy(false);
    }
  }

  async function loadTemplate(name: string) {
    setIsBusy(true);
    try {
      setContent(await readText(`/api/v1/playbook/templates/${name}`));
      setPlaybookAssetSelected(true);
      setValidation(null);
      setResult(null);
      setSelectedStage(0);
      setNotice({ severity: 'ok', message: `${formatTemplateName(name)} loaded.` });
    } catch (error) {
      setNotice({ severity: 'error', message: `Template load failed. ${(error as Error).message}` });
    } finally {
      setIsBusy(false);
    }
  }

  async function validateCurrent() {
    setIsBusy(true);
    setNotice(null);
    try {
      const body = await readJson<ValidationResponse>('/api/v1/playbook/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      setValidation(body);
      if (body.valid) setSelectedStage(1);
      setNotice({
        severity: body.valid ? 'ok' : 'warning',
        message: body.valid ? 'Playbook validated. It is ready to run.' : 'Validation found blocking issues.',
      });
    } catch (error) {
      setNotice({ severity: 'error', message: `Validation failed. ${(error as Error).message}` });
    } finally {
      setIsBusy(false);
    }
  }

  async function runPlaybook() {
    // Run is the main UI-to-backend path: validate, execute graph, fetch audit artifacts.
    setIsBusy(true);
    setNotice(null);
    try {
      const runBody = await readJson<{ submission_id: string }>('/api/v1/playbook/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      const runResult = await readJson<PlaybookResult>(`/api/v1/playbook/${runBody.submission_id}/results`);
      setResult(runResult);
      setSelectedStage(5);
      setPage('workspace');
      setWorkspaceOutcome({
        action: 'Run Playbook',
        status: 'Decision package ready',
        detail: `Run ${runBody.submission_id} completed. Reports, audit records, and layer events are available.`,
        stage: 5,
        severity: 'ok',
        updatedAt: new Date().toLocaleTimeString(),
      });
      setNotice({ severity: 'ok', message: 'Playbook run completed. Decision package is ready.' });
      refreshPlatformData();
    } catch (error) {
      setNotice({ severity: 'error', message: `Playbook run failed. ${(error as Error).message}` });
    } finally {
      setIsBusy(false);
    }
  }

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    file.text().then((value) => {
      setContent(value);
      setPlaybookAssetSelected(true);
      setValidation(null);
      setResult(null);
      setSelectedStage(0);
      setNotice({ severity: 'ok', message: `${file.name} loaded.` });
    });
  }

  function updatePlaybookContent(value: string) {
    setContent(value);
    setPlaybookAssetSelected(Boolean(value.trim()));
    setValidation(null);
    setResult(null);
    setSelectedStage(0);
  }

  async function handleWorkspaceAction(action: string, index: number) {
    const updatedAt = new Date().toLocaleTimeString();
    if (index === 0) {
      setSelectedStage(4);
      setPage('queue');
      setWorkspaceOutcome({
        action,
        status: 'Review queue opened',
        detail: `${domain.queue} is focused so a reviewer can act on the recommendation and append the final decision.`,
        stage: 4,
        severity: 'ok',
        updatedAt,
      });
      setNotice({ severity: 'ok', message: `${domain.queue} opened for ${domain.label}.` });
      return;
    }

    if (!result?.run?.submission_id) {
      setSelectedStage(1);
      setPage('studio');
      setWorkspaceOutcome({
        action,
        status: 'Run required',
        detail: 'Run a Playbook first so the UI can download a real report or audit package from the backend.',
        stage: 1,
        severity: 'warning',
        updatedAt,
      });
      setNotice({ severity: 'warning', message: 'Run a Playbook before downloading generated packages.' });
      return;
    }

    const isAudit = action.toLowerCase().includes('audit');
    const suffix = isAudit ? 'audit-record' : 'report';
    try {
      await downloadJsonFile(
        `/api/v1/playbook/${result.run.submission_id}/${suffix}`,
        `${result.run.submission_id}-${suffix}.json`,
      );
      setSelectedStage(5);
      setWorkspaceOutcome({
        action,
        status: isAudit ? 'Audit package downloaded' : 'Decision report downloaded',
        detail: `${action} used run ${result.run.submission_id}. The package reflects the current backend result.`,
        stage: 5,
        severity: 'ok',
        updatedAt,
      });
      setNotice({ severity: 'ok', message: `${action} downloaded.` });
    } catch (error) {
      setWorkspaceOutcome({
        action,
        status: 'Download failed',
        detail: (error as Error).message,
        stage: 5,
        severity: 'warning',
        updatedAt,
      });
      setNotice({ severity: 'error', message: `${action} failed. ${(error as Error).message}` });
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">{domain.mark}</div>
          <div>
            <strong>Agentic Decisioning Fabric</strong>
            <span>Domain-independent regulated decision platform</span>
            <span>Author: Sarala Biswal</span>
          </div>
        </div>
        <div className="topbar-context">
          <span>Decision setup</span>
          <strong>Select a domain, then choose the audience view</strong>
          <small>{domain.caseType} · {domain.jurisdiction} · {personaLabels[persona]} view</small>
        </div>
        <div className="top-controls">
          <label className="top-control-block">
            <span>Domain</span>
            <select value={domainKey} onChange={(event) => setDomainKey(event.target.value as DomainKey)}>
              {Object.values(domainConfigs).map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <div className="top-control-block">
            <span>View mode</span>
            <div className="persona-switch" role="group" aria-label="View mode">
              {(['business', 'technical', 'compare'] as Persona[]).map((item) => (
                <button
                  key={item}
                  className={persona === item ? 'active' : ''}
                  onClick={() => setPersona(item)}
                  title={item === 'compare' ? 'Show business and technical views together' : `Show ${personaLabels[item].toLowerCase()} view`}
                >
                  {personaLabels[item]}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      <aside className="sidebar">
        <nav>
          <p>Workspace</p>
          <NavButton page="workspace" active={page} setPage={setPage} icon={<Icon size={16} />} label={domain.workspace} />
          <NavButton page="studio" active={page} setPage={setPage} icon={<BookOpenCheck size={16} />} label="Playbook Studio" />
          <NavButton page="queue" active={page} setPage={setPage} icon={<ClipboardList size={16} />} label={domain.queue} />
          <NavButton page="audit" active={page} setPage={setPage} icon={<Scale size={16} />} label="Audit & Reports" />
          <NavButton page="architecture" active={page} setPage={setPage} icon={<Layers3 size={16} />} label="Architecture" />
          <NavButton page="settings" active={page} setPage={setPage} icon={<SlidersHorizontal size={16} />} label="Settings" />
          <p className="technical-only">Platform</p>
          <NavButton page="operations" active={page} setPage={setPage} icon={<ServerCog size={16} />} label="Operations" technical />
        </nav>
      </aside>

      <section className="main">
        {notice && <Notice notice={notice} onDismiss={() => setNotice(null)} />}
        {page === 'workspace' && (
          <DecisionWorkspace
            domain={domain}
            selectedStage={selectedStage}
            setSelectedStage={setSelectedStage}
            result={result}
            validation={validation}
            playbookAssetSelected={playbookAssetSelected}
            summary={summary}
            persona={persona}
            workspaceOutcome={workspaceOutcome}
            setPage={setPage}
            onAction={handleWorkspaceAction}
          />
        )}
        {page === 'studio' && (
          <PlaybookStudio
            domain={domain}
            templates={filteredTemplates}
            content={content}
            setContent={updatePlaybookContent}
            loadTemplate={loadTemplate}
            validateCurrent={validateCurrent}
            runPlaybook={runPlaybook}
            handleFile={handleFile}
            validation={validation}
            result={result}
            playbookAssetSelected={playbookAssetSelected}
            setPage={setPage}
            isBusy={isBusy}
          />
        )}
        {page === 'queue' && (
          <ReviewQueue
            domain={domain}
            cases={cases}
            onRefresh={refreshPlatformData}
            onDecision={decideWorkbenchCase}
            isBusy={isBusy}
          />
        )}
        {page === 'audit' && <AuditReports domain={domain} result={result} cases={cases} setPage={setPage} />}
        {page === 'architecture' && (
          <ArchitectureStoryboard
            domain={domain}
            persona={persona}
            result={result}
            runtimeConfig={runtimeConfig}
            health={health}
            streamInspection={streamInspection}
            models={models}
            setPage={setPage}
          />
        )}
        {page === 'settings' && (
          <SettingsPage
            runtimeConfig={runtimeConfig}
            health={health}
            streamInspection={streamInspection}
            isBusy={isBusy}
            onApply={updateRuntimeSettings}
            onRefresh={refreshPlatformData}
          />
        )}
        {page === 'operations' && <Operations domain={domain} health={health} models={models} result={result} />}
      </section>
    </main>
  );
}

/**
 * Navigation item that keeps page state and iconography consistent across the shell.
 */
function NavButton({
  page,
  active,
  setPage,
  icon,
  label,
  technical,
}: {
  page: Page;
  active: Page;
  setPage: (page: Page) => void;
  icon: React.ReactNode;
  label: string;
  technical?: boolean;
}) {
  return (
    <button className={classNames(['nav-link', active === page && 'active', technical && 'technical-only'])} onClick={() => setPage(page)}>
      <span className="nav-icon">{icon}</span>
      <span>{label}</span>
    </button>
  );
}

/**
 * Dismissible status message used for API and workflow feedback.
 */
function Notice({ notice, onDismiss }: { notice: UiNotice; onDismiss: () => void }) {
  return (
    <div className={classNames(['notice', notice.severity])}>
      {notice.severity === 'error' ? <XCircle size={16} /> : notice.severity === 'warning' ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
      <span>{notice.message}</span>
      <button onClick={onDismiss} aria-label="Dismiss">
        <XCircle size={15} />
      </button>
    </div>
  );
}

/**
 * First landing page for a domain.
 *
 * Shows the current decision state and moves the user to the next required action:
 * select a Playbook, validate it, run it, route for review, or open audit output.
 */
function DecisionWorkspace({
  domain,
  selectedStage,
  setSelectedStage,
  result,
  validation,
  playbookAssetSelected,
  summary,
  persona,
  workspaceOutcome,
  setPage,
  onAction,
}: {
  domain: DomainConfig;
  selectedStage: number;
  setSelectedStage: (stage: number) => void;
  result: PlaybookResult | null;
  validation: ValidationResponse | null;
  playbookAssetSelected: boolean;
  summary: AnalyticsSummary | null;
  persona: Persona;
  workspaceOutcome: WorkspaceOutcome;
  setPage: (page: Page) => void;
  onAction: (action: string, index: number) => void;
}) {
  const stage = domain.flow[selectedStage];
  const hasRun = Boolean(result?.run);
  const playbookName = validation?.playbook?.playbook.name || domain.playbook;
  const validationReady = Boolean(validation?.valid);
  const decision = result?.run?.final_decision || (validationReady ? 'Ready to run' : playbookAssetSelected ? 'Playbook selected' : 'No decision run yet');
  const outcomeStage = domain.flow[workspaceOutcome.stage] || domain.flow[selectedStage];
  const currentRunLabel = result?.run?.submission_id ? `Run ${result.run.submission_id.slice(0, 8).toUpperCase()}` : 'No run';
  const stageStatus = hasRun
    ? selectedStage < 4
      ? 'Complete'
      : selectedStage === 4
        ? 'In review'
        : 'Package ready'
    : validationReady
      ? 'Ready to run'
      : playbookAssetSelected
        ? 'Needs validation'
        : 'Needs Playbook';
  const nextStep = hasRun
    ? {
        label: result?.run?.final_decision?.toLowerCase().includes('accept') ? 'Open audit report' : domain.actions[0],
        detail: result?.run?.final_decision?.toLowerCase().includes('accept')
          ? 'Review the generated report, audit record, and trace package.'
          : `Route the generated package to ${domain.queue.toLowerCase()}.`,
        target: result?.run?.final_decision?.toLowerCase().includes('accept') ? 'Audit' : 'Open',
        action: () => (result?.run?.final_decision?.toLowerCase().includes('accept') ? setPage('audit') : onAction(domain.actions[0], 0)),
        icon: result?.run?.final_decision?.toLowerCase().includes('accept') ? Scale : ClipboardList,
      }
    : validationReady
      ? {
          label: 'Run Playbook and open outcome',
          detail: 'Execute the validated policy asset to create a decision package.',
          target: 'Run',
          action: () => setPage('studio'),
          icon: Play,
        }
      : playbookAssetSelected
        ? {
            label: 'Validate selected Playbook',
            detail: 'Check schema, required fields, policy constraints, and governance readiness.',
            target: 'Check',
            action: () => setPage('studio'),
            icon: BookOpenCheck,
          }
        : {
            label: 'Select template or upload YAML',
            detail: `Start with a ${domain.label.toLowerCase()} policy asset before evaluating a case.`,
            target: 'Start',
            action: () => setPage('studio'),
            icon: BookOpenCheck,
          };
  const NextIcon = nextStep.icon;
  const cockpitSummary = hasRun
    ? `Run ${result?.run?.submission_id} completed from ${playbookName}. The cockpit is now showing the generated outcome, evidence, audit identifier, and reviewer path.`
    : validationReady
      ? `${playbookName} is schema-valid and ready to execute. Run it to generate a real decision package.`
      : playbookAssetSelected
        ? `${playbookName} is selected. Validate it before running the regulated decision flow.`
        : `No decision run exists yet. Select a predefined ${domain.label.toLowerCase()} template or upload YAML in Playbook Studio.`;
  return (
    <>
      <header className="page-head cockpit-head">
        <div className="page-title">
          <p className="eyebrow">Decision cockpit</p>
          <h1>{domain.title}</h1>
          <p>{cockpitSummary}</p>
          <div className="tag-row">
            <span className="tag blue">{domain.caseType}</span>
            <span className="tag blue">{domain.jurisdiction}</span>
            <span className="tag blue">{playbookName}</span>
            <span className={classNames(['tag', hasRun ? 'green' : 'amber'])}>{hasRun ? 'Outcome ready' : 'Action required'}</span>
          </div>
        </div>
        <aside className="outcome-card cockpit-command-card">
          <div className="cockpit-status-row">
            <div>
              <p className="eyebrow">Current decision state</p>
              <h2>{decision}</h2>
            </div>
            <span className={classNames(['tag', hasRun ? 'amber' : validationReady ? 'green' : 'blue'])}>
              {hasRun ? domain.outcomeTag : validationReady ? 'Validated' : 'Start'}
            </span>
          </div>
          <button className="cockpit-command-action" onClick={nextStep.action}>
            <NextIcon size={17} />
            <span>
              <small>Next action</small>
              <strong>{nextStep.label}</strong>
            </span>
            <em>{nextStep.target}</em>
          </button>
          <div className="metrics">
            <Metric label={hasRun ? domain.metricOne[0] : 'Playbook'} value={playbookAssetSelected ? 'Selected' : 'Needed'} />
            <Metric label={hasRun ? domain.metricTwo[0] : 'Validation'} value={validationReady ? 'Passed' : 'Pending'} />
            <Metric label="Runs" value={summary?.total_submissions ?? 0} />
          </div>
        </aside>
      </header>

      <nav className="business-flow" aria-label="Domain flow">
        {domain.flow.map((item, index) => (
          <button
            key={item[0]}
            className={classNames(['flow-step', index < selectedStage && 'complete', index === selectedStage && 'active'])}
            onClick={() => setSelectedStage(index)}
          >
            <span>Stage {index + 1}</span>
            <strong>{item[0]}</strong>
            <small>{item[1]}</small>
          </button>
        ))}
      </nav>

      <section className="workspace-grid">
        <aside className="panel">
          <div className="panel-head">
            <h2>Decision flow</h2>
            <span className="tag blue">{currentRunLabel}</span>
          </div>
          <div className="panel-body stage-list">
            <div className="cockpit-next-card">
              <span>Start here</span>
              <strong>{nextStep.label}</strong>
              <p>{nextStep.detail}</p>
              <button className="cockpit-primary-action" onClick={nextStep.action}>
                <NextIcon size={16} />
                {nextStep.label}
                <span>{nextStep.target}</span>
              </button>
            </div>
            {domain.flow.map((item, index) => (
              <button
                className={classNames(['stage-button', index === selectedStage && 'active'])}
                key={item[0]}
                onClick={() => setSelectedStage(index)}
              >
                <span className="stage-number">{index + 1}</span>
                <span>
                  <strong>{item[0]}</strong>
                  <small>{item[2]}</small>
                </span>
              </button>
            ))}
          </div>
        </aside>

        <article className="panel decision-panel">
          <div className="decision-hero">
            <div>
              <p className="eyebrow">Stage {selectedStage + 1}</p>
              <h2>{stage[0]}</h2>
              <p>{stage[2]}</p>
            </div>
            <div className="hero-facts">
              <Fact label="Status" value={stageStatus} />
              <Fact label="Owner" value={selectedStage < 2 ? 'Intake' : selectedStage < 4 ? 'Decision engine' : 'Workbench'} />
              <Fact
                label="Evidence"
                value={result?.layer_events.length ? `${result.layer_events.length} events` : validationReady ? 'Validated' : 'Pending'}
              />
            </div>
          </div>

          <div className="persona-grid">
            <PersonaLens
              className="business-lens"
              title="Business View"
              tag="Decision clarity"
              body={businessNarrative(domain, selectedStage)}
              bullets={businessBullets(domain, selectedStage)}
            />
            <PersonaLens
              className="technical-lens"
              title="Technical View"
              tag="Execution proof"
              body={technicalNarrative(domain, selectedStage)}
              bullets={technicalBullets(domain, selectedStage, result)}
            />
          </div>

          <div className="evidence-grid">
            {evidenceCards(domain, selectedStage, result).map((card) => (
              <article className="evidence-card" key={card[0]}>
                <span>{card[0]}</span>
                <strong>{card[1]}</strong>
                <p>{card[2]}</p>
              </article>
            ))}
          </div>
        </article>

        <aside className="side-stack">
          <section className="panel">
            <div className="panel-head">
              <h3>Case facts</h3>
              <span className={classNames(['tag', hasRun ? 'amber' : 'blue'])}>{hasRun ? domain.outcomeTag : 'Not run'}</span>
            </div>
            <div className="panel-body fact-list">
              <FactRow label={domain.facts[0][0]} value={result?.run?.submission_id || 'Not generated'} />
              <FactRow label={domain.facts[1][0]} value={result?.rule_events[0]?.display || (hasRun ? domain.facts[1][1] : 'Awaiting run')} />
              <FactRow label={domain.facts[2][0]} value={domain.facts[2][1]} />
              <FactRow label={domain.facts[3][0]} value={result?.audit_records[0]?.audit_id || 'Not generated'} />
              <FactRow label="Persona" value={persona} />
            </div>
          </section>
          <section className="panel">
            <div className="panel-head">
              <h3>Next actions</h3>
            </div>
            <div className="panel-body action-list">
              {!hasRun && (
                <button className="action-button primary" onClick={() => setPage('studio')}>
                  Open Playbook Studio
                  <span>{validationReady ? 'Run' : playbookAssetSelected ? 'Validate' : 'Select'}</span>
                </button>
              )}
              {hasRun &&
                domain.actions.map((action, index) => (
                  <button
                    className={classNames(['action-button', index === 0 && 'primary'])}
                    key={action}
                    onClick={() => onAction(action, index)}
                  >
                    {action}
                    <span>{index === 0 ? 'Open' : 'Get'}</span>
                  </button>
                ))}
              <div className={classNames(['action-outcome', workspaceOutcome.severity])}>
                <span>Selected action</span>
                <strong>{workspaceOutcome.action}</strong>
                <p>{workspaceOutcome.detail}</p>
                <small>
                  Outcome: {workspaceOutcome.status} · Focus: {outcomeStage[0]} · {workspaceOutcome.updatedAt}
                </small>
              </div>
            </div>
          </section>
        </aside>
      </section>
    </>
  );
}

/**
 * Playbook authoring and execution workspace.
 *
 * Guides users through seeded template selection, validation, run, and outcome review
 * while keeping uploaded YAML visible and editable.
 */
function PlaybookStudio({
  domain,
  templates,
  content,
  setContent,
  loadTemplate,
  validateCurrent,
  runPlaybook,
  handleFile,
  validation,
  result,
  playbookAssetSelected,
  setPage,
  isBusy,
}: {
  domain: DomainConfig;
  templates: TemplateSummary[];
  content: string;
  setContent: (content: string) => void;
  loadTemplate: (name: string) => void;
  validateCurrent: () => void;
  runPlaybook: () => void;
  handleFile: (event: ChangeEvent<HTMLInputElement>) => void;
  validation: ValidationResponse | null;
  result: PlaybookResult | null;
  playbookAssetSelected: boolean;
  setPage: (page: Page) => void;
  isBusy: boolean;
}) {
  const [selectedBlock, setSelectedBlock] = useState(0);
  const [studioView, setStudioView] = useState<'overview' | 'rules' | 'yaml'>('overview');
  const validationStatus = validation
    ? validation.valid
      ? 'Validated'
      : 'Needs correction'
    : playbookAssetSelected
      ? 'Ready to validate'
      : 'Waiting for asset';
  const resultStatus = result?.run ? 'Outcome available' : 'Not run';
  const selectedPolicyName = validation?.playbook?.playbook.name || (playbookAssetSelected ? domain.playbook : 'No Playbook selected');
  const selectedVersion = validation?.playbook?.playbook.version || (playbookAssetSelected ? domain.playbook.split(' v')[1] || 'draft' : 'none');
  const selectedBlockData = domain.playbookBlocks[selectedBlock] || domain.playbookBlocks[0];
  const currentStep = !playbookAssetSelected ? 1 : !validation || !validation.valid ? 2 : result?.run ? 4 : 3;
  const nextAction =
    currentStep === 1
      ? `Choose one of the ${templates.length || 5} seeded templates`
      : currentStep === 2
        ? validation?.valid === false
          ? 'Fix validation findings'
          : 'Validate the selected Playbook'
        : currentStep === 3
          ? 'Run the validated Playbook'
          : 'Open the generated outcome';
  const nextActionDetail =
    currentStep === 1
      ? 'Use the Policy asset library on the left. Pick one seeded template to load a complete policy asset, or upload YAML for a custom Playbook.'
      : currentStep === 2
        ? validation?.valid === false
          ? 'Resolve the blocking validation findings before execution.'
          : 'Confirm the selected policy asset is schema-valid before running it.'
        : currentStep === 3
          ? 'Validation passed. Run the Playbook to generate a decision, audit, and trace package.'
          : 'A decision package is available. Open the workspace or audit report.';
  const workflowSteps = [
    {
      step: 1,
      label: '1 · Select',
      title: currentStep === 1 ? 'Select a policy asset' : selectedPolicyName,
      detail: 'Choose a template or upload YAML.',
      state: currentStep === 1 ? 'current' : 'complete',
      action: () => setStudioView('overview'),
    },
    {
      step: 2,
      label: '2 · Validate',
      title: validationStatus,
      detail: validation?.valid === false ? 'Fix blocking findings.' : 'Check schema and domain rules.',
      state: validation?.valid ? 'complete' : currentStep === 2 ? (validation ? 'warning current' : 'current') : '',
      action: validateCurrent,
    },
    {
      step: 3,
      label: '3 · Run',
      title: resultStatus,
      detail: 'Generate decision, audit, and trace.',
      state: result?.run ? 'complete' : currentStep === 3 ? 'current' : '',
      action: runPlaybook,
    },
    {
      step: 4,
      label: '4 · Outcome',
      title: result?.run ? 'Open workspace' : 'Waiting for run',
      detail: 'Review result and download package.',
      state: currentStep === 4 ? 'current complete' : '',
      action: () => setPage(result?.run ? 'workspace' : 'studio'),
    },
  ];
  return (
    <>
      <header className="page-head single">
        <div className="page-title">
          <p className="eyebrow">Playbook Studio</p>
          <h1>{domain.label} decision asset</h1>
          <p>Select a policy asset, inspect its business rules, validate it, then run the regulated decision flow.</p>
        </div>
      </header>
      <section className="workflow-next-panel" aria-label="Playbook next action">
        <div className="workflow-next-copy">
          <span>Next action</span>
          <h2>{nextAction}</h2>
          <p>{nextActionDetail}</p>
        </div>
        <div className="workflow-next-actions">
          {currentStep === 1 && (
            <>
              <a className="primary-button template-library-jump" href="#policy-asset-library">
                <FileText size={16} />
                Review seeded templates <span>Left panel</span>
              </a>
              <label className="file-button next-upload-button">
                Upload custom YAML
                <input type="file" accept=".yaml,.yml" onChange={handleFile} />
              </label>
            </>
          )}
          {currentStep === 2 && (
            <button className="primary-button" onClick={validateCurrent} disabled={isBusy}>
              {isBusy ? <Loader2 className="spin" size={16} /> : <BookOpenCheck size={16} />}
              Validate Playbook <span>Check</span>
            </button>
          )}
          {currentStep === 3 && (
            <button className="primary-button" onClick={runPlaybook} disabled={isBusy || !validation?.valid}>
              <Play size={16} />
              Run Playbook <span>Run</span>
            </button>
          )}
          {currentStep === 4 && (
            <button className="primary-button" onClick={() => setPage('workspace')} disabled={!result?.run}>
              Open generated outcome <span>Open</span>
            </button>
          )}
        </div>
      </section>

      <section className="flow-guide action-flow-guide">
        {workflowSteps.map((step) => (
          <button
            key={step.step}
            className={classNames(['guide-step', step.state])}
            onClick={step.action}
            disabled={
              isBusy ||
              (step.step === 2 && !playbookAssetSelected) ||
              (step.step === 3 && !validation?.valid) ||
              (step.step === 4 && !result?.run)
            }
          >
            <span>{step.label}</span>
            <strong>{step.title}</strong>
            <small>{step.detail}</small>
          </button>
        ))}
      </section>

      <section className="playbook-workbench">
        <aside id="policy-asset-library" className={classNames(['panel', 'playbook-library', currentStep === 1 && 'needs-selection'])}>
          <div className="panel-head">
            <h3>Policy asset library</h3>
            <span className="tag blue">{templates.length || 5} seeded templates</span>
          </div>
          <div className="panel-body">
            {currentStep === 1 && (
              <div className="library-step-callout">
                <span>Step 1</span>
                <strong>Select one template below</strong>
                <p>These seeded templates are ready to inspect, validate, and run for the selected domain.</p>
              </div>
            )}
            <div className="asset-current">
              <span>Current draft</span>
              <strong>{selectedPolicyName}</strong>
              <small>{domain.caseType} · {domain.jurisdiction} · v{selectedVersion}</small>
            </div>
            <div className="template-list asset-list">
              {(templates.length ? templates : [{ name: `playbook_${domain.key}_sample.yaml`, size_bytes: 0 }]).map((template) => (
                <button key={template.name} onClick={() => loadTemplate(template.name)}>
                  <FileText size={16} />
                  <span>
                    <strong>{formatTemplateName(template.name)}</strong>
                    <small>Seeded {domain.label} policy asset</small>
                  </span>
                </button>
              ))}
            </div>
            <label className="file-button upload-asset-button">
              Upload custom YAML
              <input type="file" accept=".yaml,.yml" onChange={handleFile} />
            </label>
          </div>
        </aside>

        <article className="panel playbook-builder">
          <div className="panel-head">
            <h2>Playbook Builder</h2>
            <span className="tag blue">{domain.playbook}</span>
          </div>
          <div className="panel-body">
            <div className="builder-summary">
              <div>
                <span>Decision policy</span>
                <h2>{selectedPolicyName}</h2>
                <p>{domain.summary}</p>
              </div>
              <div className="hero-facts">
                <Fact label="Domain" value={domain.label} />
                <Fact label="Case type" value={domain.caseType} />
                <Fact label="Jurisdiction" value={domain.jurisdiction} />
              </div>
            </div>

            <div className="builder-tabs" role="group" aria-label="Playbook editor view">
              {(['overview', 'rules', 'yaml'] as const).map((view) => (
                <button
                  className={studioView === view ? 'active' : ''}
                  key={view}
                  onClick={() => setStudioView(view)}
                >
                  {view === 'yaml' ? 'YAML' : view.charAt(0).toUpperCase() + view.slice(1)}
                </button>
              ))}
            </div>

            {studioView === 'overview' && (
              <>
                <div className="canvas playbook-canvas" aria-label="Visual Playbook canvas">
                  {domain.playbookBlocks.map((block, index) => (
                    <button
                      className={classNames(['canvas-block', selectedBlock === index && 'active'])}
                      key={block[0]}
                      onClick={() => setSelectedBlock(index)}
                    >
                      <span>{index + 1}</span>
                      <strong>{block[0]}</strong>
                      <small>{block[1]}</small>
                    </button>
                  ))}
                </div>
                <div className="builder-detail">
                  <div>
                    <span>Selected section</span>
                    <h3>{selectedBlockData[0]}</h3>
                    <p>{selectedBlockData[1]}</p>
                  </div>
                  <ul className="bullet-list">
                    <li><span className="dot" /><span>Business owners can inspect this section before execution.</span></li>
                    <li><span className="dot" /><span>Validation checks schema, policy constraints, and required fields.</span></li>
                    <li><span className="dot" /><span>The run creates decision, audit, and trace records.</span></li>
                  </ul>
                </div>
              </>
            )}

            {studioView === 'rules' && (
              <div className="rules-grid">
                {domain.playbookBlocks.map((block) => (
                  <div className="rule-card" key={block[0]}>
                    <span>{block[0]}</span>
                    <strong>{block[1]}</strong>
                    <p>{block[0] === 'Governance' ? 'Controls review triggers, prohibited factors, notices, and audit retention.' : 'Mapped into typed execution inputs for the domain adapter and agents.'}</p>
                  </div>
                ))}
              </div>
            )}

            {studioView === 'yaml' && (
              <div className="yaml-editor">
                <div className="editor-toolbar">
                  <span>Advanced source editor</span>
                  <label className="file-button">
                    Upload YAML
                    <input type="file" accept=".yaml,.yml" onChange={handleFile} />
                  </label>
                </div>
                <textarea value={content} onChange={(event) => setContent(event.target.value)} />
              </div>
            )}
          </div>
        </article>

        <aside className="panel playbook-action-rail">
          <div className="panel-head">
            <h3>Action rail</h3>
            <span className="tag green">Next</span>
          </div>
          <div className="panel-body">
            <div className={classNames(['action-outcome', validation && !validation.valid && 'warning'])}>
              <span>Recommended action</span>
              <strong>{nextAction}</strong>
              <p>{nextActionDetail}</p>
            </div>

            <div className="action-list studio-primary-actions">
              <button
                className={classNames(['action-button', !validation?.valid && 'primary'])}
                onClick={validateCurrent}
                disabled={isBusy || !playbookAssetSelected}
              >
                {isBusy ? <Loader2 className="spin" size={16} /> : <BookOpenCheck size={16} />}
                Validate Playbook <span>Check</span>
              </button>
              <button
                className={classNames(['action-button', validation?.valid && !result?.run && 'primary'])}
                onClick={runPlaybook}
                disabled={isBusy || !validation?.valid}
              >
                <Play size={16} />
                Run Playbook and open outcome <span>Run</span>
              </button>
              <button className="action-button" onClick={() => setPage(result?.run ? 'workspace' : 'audit')} disabled={!result?.run}>
                Open generated package <span>Open</span>
              </button>
            </div>

            <MessageList messages={validation?.messages || []} />

            <div className="simulation-block">
              <div className="panel-subhead">
                <h3>Simulation impact</h3>
                <span className="tag amber">Draft vs current</span>
              </div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Current</th>
                    <th>Draft</th>
                  </tr>
                </thead>
                <tbody>
                  {domain.simulation.map((row) => (
                    <tr key={row[0]}>
                      <td>{row[0]}</td>
                      <td>{row[1]}</td>
                      <td>{row[2]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </aside>
      </section>
    </>
  );
}

/**
 * Human review workbench for escalated cases.
 *
 * Lets reviewers inspect the same business and technical rationale before appending
 * confirm, override, or information-request actions to the audit trail.
 */
function ReviewQueue({
  domain,
  cases,
  onRefresh,
  onDecision,
  isBusy,
}: {
  domain: DomainConfig;
  cases: WorkbenchCase[];
  onRefresh: () => void;
  onDecision: (caseId: string, decision: string, notes: string) => Promise<void>;
  isBusy: boolean;
}) {
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<'pending' | 'decided' | 'all'>('pending');
  const [notes, setNotes] = useState('Reviewed evidence and recommendation. Decision is ready for audit append.');
  const domainCases = useMemo(
    () => cases.filter((item) => item.submission.domain === domain.key),
    [cases, domain.key],
  );
  const filteredCases = useMemo(
    () => domainCases.filter((item) => statusFilter === 'all' || item.status === statusFilter),
    [domainCases, statusFilter],
  );
  const selected = domainCases.find((item) => item.case_id === selectedCaseId) || filteredCases[0] || domainCases[0] || null;
  const latestAgent = selected?.agent_outputs[selected.agent_outputs.length - 1];
  const reviewReasons = selected ? queueReviewReasons(selected) : businessBullets(domain, 4);
  const evidence = selected ? queueEvidenceCards(selected, domain) : evidenceCards(domain, 4, null);
  const pendingCount = domainCases.filter((item) => item.status === 'pending').length;
  const decidedCount = domainCases.filter((item) => item.status === 'decided').length;
  const canAppend = Boolean(selected && selected.status !== 'decided');
  const [reviewOutcome, setReviewOutcome] = useState<WorkspaceOutcome>({
    action: 'Select reviewer action',
    status: selected ? 'Case ready' : 'Sample queue',
    detail: selected
      ? 'A backend workbench case is available for reviewer action.'
      : 'No backend case is loaded for this domain yet; run a Playbook to populate the live queue.',
    stage: 4,
    severity: selected ? 'ok' : 'warning',
    updatedAt: 'Ready',
  });

  useEffect(() => {
    setSelectedCaseId((current) => {
      if (current && domainCases.some((item) => item.case_id === current)) return current;
      return filteredCases[0]?.case_id || domainCases[0]?.case_id || null;
    });
  }, [domain.key, cases, domainCases, filteredCases]);

  useEffect(() => {
    setReviewOutcome((current) => {
      if (current.action !== 'Select reviewer action' && current.action !== 'Review case') return current;
      return {
        action: selected ? 'Review case' : 'Select reviewer action',
        status: selected ? 'Case ready' : 'No live case',
        detail: selected
          ? `${queueCaseLabel(domain, selected)} is ready for evidence review and reviewer action.`
          : `Run a Playbook to create a live ${domain.queue.toLowerCase()} case.`,
        stage: 4,
        severity: selected ? 'ok' : 'warning',
        updatedAt: 'Ready',
      };
    });
  }, [domain, selected]);

  async function applyReviewAction(action: string, decision: string, status: string) {
    if (!selected) {
      setReviewOutcome({
        action,
        status: 'Run a Playbook first',
        detail: `No ${domain.queue.toLowerCase()} case exists yet. Run a Playbook to populate the live reviewer queue.`,
        stage: 4,
        severity: 'warning',
        updatedAt: new Date().toLocaleTimeString(),
      });
      return;
    }
    setReviewOutcome({
      action,
      status: 'Appending action',
      detail: `${action} is being written as an append-only reviewer action for ${queueCaseLabel(domain, selected)}.`,
      stage: 4,
      severity: 'ok',
      updatedAt: new Date().toLocaleTimeString(),
    });
    try {
      await onDecision(selected.case_id, decision, notes);
      setReviewOutcome({
        action,
        status,
        detail: `${action} was appended for ${queueCaseLabel(domain, selected)}. The audit trail now has the reviewer action and supporting notes.`,
        stage: 4,
        severity: 'ok',
        updatedAt: new Date().toLocaleTimeString(),
      });
    } catch (error) {
      setReviewOutcome({
        action,
        status: 'Action failed',
        detail: (error as Error).message,
        stage: 4,
        severity: 'warning',
        updatedAt: new Date().toLocaleTimeString(),
      });
    }
  }

  function selectCase(caseId: string) {
    setSelectedCaseId(caseId);
    setReviewOutcome({
      action: 'Review case',
      status: 'Case selected',
      detail: `Reviewer workspace loaded ${caseId}. Evidence, reasons, and action controls are ready.`,
      stage: 4,
      severity: 'ok',
      updatedAt: new Date().toLocaleTimeString(),
    });
  }
  return (
    <>
      <header className="page-head single">
        <div className="page-title">
          <p className="eyebrow">{domain.queue}</p>
          <h1>Human review workbench</h1>
          <p>Reviewer queue for escalated decisions, evidence inspection, action capture, and append-only audit.</p>
          <div className="tag-row">
            <span className="tag blue">{pendingCount} pending</span>
            <span className="tag green">{decidedCount} decided</span>
            <span className="tag">{domainCases.length} total</span>
          </div>
        </div>
        <button className="refresh-button" onClick={onRefresh}>
          <RefreshCw size={16} /> Refresh
        </button>
      </header>
      <section className="queue-grid">
        <Panel title="Reviewer worklist" tag={`${filteredCases.length} shown`}>
          <div className="queue-filter" role="group" aria-label="Queue filter">
            {(['pending', 'decided', 'all'] as const).map((filter) => (
              <button
                className={statusFilter === filter ? 'active' : ''}
                key={filter}
                onClick={() => setStatusFilter(filter)}
              >
                {filter.charAt(0).toUpperCase() + filter.slice(1)}
              </button>
            ))}
          </div>
          <div className="queue-worklist">
            {filteredCases.length ? (
              filteredCases.map((item) => (
                <button
                  className={classNames(['queue-case-row', selected?.case_id === item.case_id && 'active'])}
                  key={item.case_id}
                  onClick={() => selectCase(item.case_id)}
                >
                  <span className="queue-case-status">{item.status}</span>
                  <strong>{queueCaseLabel(domain, item)}</strong>
                  <small>{caseTypeLabel(item.submission.case_type)} · {item.submission.jurisdiction}</small>
                  <div className="queue-row-metrics">
                    <span>{formatPercent(item.confidence)}</span>
                    <span>{item.escalation_reason || domain.outcomeTag}</span>
                  </div>
                </button>
              ))
            ) : (
              <div className="queue-empty">
                <strong>No {statusFilter === 'all' ? '' : statusFilter} cases</strong>
                <p>Run a Playbook or change the filter to inspect reviewer cases for this domain.</p>
              </div>
            )}
          </div>
        </Panel>

        <Panel title="Case review" tag={selected?.status || 'No case'}>
          <div className="queue-case-summary">
            <div>
              <span>Selected case</span>
              <h2>{selected ? queueCaseLabel(domain, selected) : 'No live case selected'}</h2>
              <p>{selected?.escalation_reason || businessNarrative(domain, 4)}</p>
            </div>
            <div className="hero-facts">
              <Fact label="Recommendation" value={selected?.agent_recommendation || domain.outcome} />
              <Fact label="Confidence" value={selected ? formatPercent(selected.confidence) : domain.metricOne[1]} />
              <Fact label="Context" value={selected?.context?.context_confidence || 'Sample'} />
            </div>
          </div>

          <div className="queue-section">
            <h3>Why this needs review</h3>
            <ul className="bullet-list">
              {reviewReasons.map((item) => (
                <li key={item}>
                  <span className="dot" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="queue-section">
            <h3>Agent rationale</h3>
            <div className="agent-stack">
              {(selected?.agent_outputs.length ? selected.agent_outputs : sampleAgentOutputs(domain)).map((agent) => (
                <div className="agent-card" key={`${agent.agent_type}-${agent.decision}`}>
                  <div>
                    <strong>{agentTypeLabel(agent.agent_type)}</strong>
                    <span>{formatPercent(agent.confidence)}</span>
                  </div>
                  <p>{agent.explanation}</p>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        <Panel title="Evidence and actions" tag="Append audit">
          <div className="queue-evidence-grid">
            {evidence.map(([title, status, detail]) => (
              <div className="evidence-card compact" key={`${title}-${status}`}>
                <span>{title}</span>
                <strong>{status}</strong>
                <p>{detail}</p>
              </div>
            ))}
          </div>

          <div className="queue-section">
            <label className="queue-notes">
              <span>Reviewer notes</span>
              <textarea value={notes} onChange={(event) => setNotes(event.target.value)} />
            </label>
          </div>

          <div className="action-list">
            <button
              className="action-button primary"
              onClick={() => applyReviewAction('Confirm recommendation', selected?.agent_recommendation || domain.outcome, 'Decision recorded')}
              disabled={isBusy || !canAppend}
            >
              Confirm recommendation <span>Audit</span>
            </button>
            <button
              className="action-button"
              onClick={() => applyReviewAction('Override with notes', 'human_override', 'Override recorded')}
              disabled={isBusy || !canAppend}
            >
              Override with notes <span>Audit</span>
            </button>
            <button
              className="action-button"
              onClick={() => applyReviewAction('Request more information', 'request_more_information', 'Follow-up recorded')}
              disabled={isBusy || !canAppend}
            >
              Request more information <span>Queue</span>
            </button>
            <div className={classNames(['action-outcome', reviewOutcome.severity])}>
              <span>Review outcome</span>
              <strong>{reviewOutcome.status}</strong>
              <p>{reviewOutcome.detail}</p>
              <small>{reviewOutcome.updatedAt}</small>
            </div>
          </div>

          <div className="queue-technical">
            <FactRow label="Submission" value={selected?.submission.submission_id || 'No live submission'} />
            <FactRow label="Latest agent" value={latestAgent ? agentTypeLabel(latestAgent.agent_type) : 'Sample'} />
            <FactRow label="Sources" value={selected?.context?.sources_available?.join(', ') || 'Core, history, external'} />
          </div>
        </Panel>
      </section>
    </>
  );
}

/**
 * Audit reconstruction page.
 *
 * Presents business report, append-only audit timeline, trace package, and governance
 * controls for the selected generated package.
 */
function AuditReports({
  domain,
  result,
  cases,
  setPage,
}: {
  domain: DomainConfig;
  result: PlaybookResult | null;
  cases: WorkbenchCase[];
  setPage: (page: Page) => void;
}) {
  const domainCases = useMemo(
    () => cases.filter((item) => item.submission.domain === domain.key),
    [cases, domain.key],
  );
  const packageOptions = useMemo(() => auditPackageOptions(domain, result, domainCases), [domain, result, domainCases]);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string | null>(null);
  const [fetchedAuditRecords, setFetchedAuditRecords] = useState<AuditRecordView[]>([]);
  const [auditLoadState, setAuditLoadState] = useState('Ready');
  const selectedPackage =
    packageOptions.find((item) => item.submissionId === selectedSubmissionId) || packageOptions[0] || null;
  const selectedCase = selectedPackage?.caseId
    ? domainCases.find((item) => item.case_id === selectedPackage.caseId) || null
    : null;
  const isResultPackage = Boolean(result?.run && selectedPackage?.submissionId === result.run.submission_id);
  const resultAuditRecords = useMemo(
    () => (isResultPackage ? result?.audit_records || [] : []),
    [isResultPackage, result?.audit_records],
  );
  const auditRecords = fetchedAuditRecords.length ? fetchedAuditRecords : resultAuditRecords;
  const traceEvents = isResultPackage && result?.layer_events.length ? result.layer_events : [];
  const ruleEvents = isResultPackage && result?.rule_events.length ? result.rule_events : [];
  const finalDecision =
    auditRecords[0]?.final_decision ||
    result?.run?.final_decision ||
    selectedCase?.human_decision ||
    selectedCase?.agent_recommendation ||
    domain.outcome;

  useEffect(() => {
    setSelectedSubmissionId((current) => {
      if (current && packageOptions.some((item) => item.submissionId === current)) return current;
      return packageOptions[0]?.submissionId || null;
    });
  }, [packageOptions]);

  useEffect(() => {
    if (!selectedPackage) {
      setFetchedAuditRecords([]);
      setAuditLoadState('No package selected');
      return;
    }
    let cancelled = false;
    setFetchedAuditRecords(resultAuditRecords);
    setAuditLoadState(resultAuditRecords.length ? 'Refreshing audit records' : 'Loading audit records');
    readJson<AuditRecordView[]>(`/api/v1/audit/${selectedPackage.submissionId}`)
      .then((records) => {
        if (cancelled) return;
        setFetchedAuditRecords(records);
        setAuditLoadState(records.length ? 'Audit records loaded' : 'No audit records found');
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setFetchedAuditRecords([]);
        setAuditLoadState(`Audit load failed: ${error.message}`);
      });
    return () => {
      cancelled = true;
    };
  }, [resultAuditRecords, selectedPackage]);

  return (
    <>
      <header className="page-head single">
        <div className="page-title">
          <p className="eyebrow">Audit & Reports</p>
          <h1>{domain.label} decision reconstruction</h1>
          <p>Regulator-ready decision narrative, append-only audit timeline, technical trace, and downloadable package.</p>
          <div className="tag-row">
            <span className="tag blue">{packageOptions.length} packages</span>
            <span className="tag green">{auditRecords.length} audit records</span>
            <span className="tag">{traceEvents.length} trace layers</span>
          </div>
        </div>
      </header>

      <section className="audit-grid">
        <Panel title="Decision package" tag="Business">
          <div className="audit-package-list">
            {packageOptions.length ? (
              packageOptions.map((item) => (
                <button
                  className={classNames(['audit-package-row', selectedPackage?.submissionId === item.submissionId && 'active'])}
                  key={`${item.source}-${item.submissionId}`}
                  onClick={() => setSelectedSubmissionId(item.submissionId)}
                >
                  <span>{item.source}</span>
                  <strong>{item.label}</strong>
                  <small>{item.subtitle}</small>
                </button>
              ))
            ) : (
              <div className="queue-empty">
                <strong>No package generated</strong>
                <p>Run a Playbook to create a decision package, audit records, and technical trace.</p>
              </div>
            )}
          </div>

          <div className="audit-decision-card">
            <span>Decision narrative</span>
            <h2>{finalDecision}</h2>
            <p>{selectedPackage?.summary || businessNarrative(domain, 5)}</p>
            <div className="metrics">
              <Metric label="Jurisdiction" value={selectedPackage?.jurisdiction || domain.jurisdiction} />
              <Metric label="Confidence" value={selectedPackage?.confidence || domain.metricOne[1]} />
              <Metric label="Status" value={selectedPackage?.status || 'Draft'} />
            </div>
          </div>

          {selectedPackage ? (
            <div className="action-list audit-actions">
              <a className="action-button primary" href={`/api/v1/playbook/${selectedPackage.submissionId}/report`}>
                Download decision report <ArrowDownToLine size={14} />
              </a>
              <a className="action-button" href={`/api/v1/playbook/${selectedPackage.submissionId}/audit-record`}>
                Download audit package <ArrowDownToLine size={14} />
              </a>
            </div>
          ) : (
            <div className="action-outcome warning audit-actions">
              <span>Next step</span>
              <strong>Generate a run</strong>
              <p>Playbook execution creates the package that this page reconstructs.</p>
              <button className="action-button" onClick={() => setPage('studio')}>
                Open Playbook Studio <span>Run</span>
              </button>
            </div>
          )}
        </Panel>

        <Panel title="Audit timeline" tag="Append-only">
          <div className="action-outcome compact">
            <span>Audit source</span>
            <strong>{auditLoadState}</strong>
            <p>Records are append-only. Human reviewer actions add new records instead of rewriting prior decisions.</p>
          </div>
          <div className="audit-timeline">
            {auditRecords.length ? (
              auditRecords.map((record, index) => (
                <div className="audit-timeline-row" key={record.audit_id}>
                  <span>{index + 1}</span>
                  <div>
                    <strong>{auditDecisionTypeLabel(record.decision_type)}</strong>
                    <p>{record.final_decision}</p>
                    <small>{record.audit_id}</small>
                    <div className="audit-rule-list">
                      {(record.governance_rules_applied || []).slice(0, 4).map((rule) => (
                        <em key={`${record.audit_id}-${rule}`}>{rule}</em>
                      ))}
                    </div>
                  </div>
                  <b>{record.governance_passed ? 'Passed' : 'Review'}</b>
                </div>
              ))
            ) : (
              <div className="queue-empty">
                <strong>No audit records yet</strong>
                <p>Run a Playbook or submit a reviewer action to append the first audit record.</p>
              </div>
            )}
          </div>
        </Panel>

        <Panel title="Trace and controls" tag="Technical">
          {traceEvents.length ? (
            <div className="audit-trace-list">
              {traceEvents.map((event) => (
                <div className="audit-trace-row" key={`${event.layer}-${event.name}`}>
                  <span>{event.layer}</span>
                  <div>
                    <strong>{event.name}</strong>
                    <small>{event.detail}</small>
                  </div>
                  <b>{event.status}</b>
                </div>
              ))}
            </div>
          ) : (
            <div className="queue-empty">
              <strong>No trace evidence yet</strong>
              <p>Run a Playbook to generate actual layer events for this decision package.</p>
            </div>
          )}

          <div className="queue-section">
            <h3>Governance checks</h3>
            <div className="mini-list">
              {(ruleEvents.length ? ruleEvents : evidenceCards(domain, 3, null).map(([rule, result, display]) => ({ rule_field: rule, result, display }))).slice(0, 5).map((event) => (
                <div className="mini-row" key={`${event.rule_field}-${event.result}`}>
                  <strong>{event.rule_field}</strong>
                  <span>{event.result}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="queue-section">
            <h3>Open workflow</h3>
            <div className="action-list">
              <button className="action-button" onClick={() => setPage('queue')}>
                Open reviewer queue <span>Review</span>
              </button>
              <button className="action-button" onClick={() => setPage('architecture')}>
                Explain architecture <span>L0-L9</span>
              </button>
            </div>
          </div>
        </Panel>
      </section>
    </>
  );
}

/**
 * Visual architecture diagram linking L0-L9 layers to the selected domain flow.
 */
function ArchitectureStoryPicture({
  domain,
  result,
  runtimeConfig,
  selectedLayer,
  setSelectedLayer,
}: {
  domain: DomainConfig;
  result: PlaybookResult | null;
  runtimeConfig: RuntimeConfig | null;
  selectedLayer: string;
  setSelectedLayer: (index: number) => void;
}) {
  const DomainIcon = domainIcons[domain.key];
  const activeNodeIndex = architectureStoryNodes.findIndex((node) => node.layers.includes(selectedLayer));
  const runtimeMode = runtimeConfig?.runtime_mode || 'mock_only';
  const decision = result?.run?.final_decision || domain.outcome;
  const runLabel = result?.run?.submission_id || 'sample run';

  return (
    <section className="architecture-picture" aria-label="Complete decisioning story">
      <div className="picture-head">
        <div>
          <p className="eyebrow">Complete Story</p>
          <h2>{domain.label} decisioning from request to proof</h2>
          <p>
            One picture of the business journey and the platform layers underneath it. Select a segment to inspect the
            matching L0-L9 implementation detail.
          </p>
        </div>
        <div className="picture-outcome">
          <DomainIcon size={20} />
          <div>
            <span>{domain.caseType}</span>
            <strong>{decision}</strong>
          </div>
        </div>
      </div>

      <div className="story-picture-canvas">
        <div className="story-lane-label business">Business journey</div>
        <div className="story-lane-label technical">Platform evidence</div>
        <div className="story-path-line business" />
        <div className="story-path-line technical" />

        <div className="story-node-row business">
          {architectureStoryNodes.map((node, index) => {
            const firstLayer = architectureLayers.findIndex((layer) => layer.id === node.layers[0]);
            return (
              <button
                className={classNames(['story-node', index === activeNodeIndex && 'active'])}
                key={node.title}
                onClick={() => setSelectedLayer(firstLayer)}
              >
                <span className="story-node-index">{index + 1}</span>
                <strong>{node.title}</strong>
                <small>{node.business}</small>
              </button>
            );
          })}
        </div>

        <div className="story-node-row technical">
          {architectureStoryNodes.map((node, index) => (
            <div className={classNames(['story-tech-node', index === activeNodeIndex && 'active'])} key={node.title}>
              <div className="story-layer-chips">
                {node.layers.map((layerId) => (
                  <span key={`${node.title}-${layerId}`}>{layerId}</span>
                ))}
              </div>
              <p>{node.technical}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="picture-footer">
        <Fact label="Runtime" value={runtimeMode.replaceAll('_', ' ')} />
        <Fact label="Run" value={runLabel} />
        <Fact label="Proof" value="audit, report, telemetry" />
      </div>
    </section>
  );
}

/**
 * Interactive L0-L9 architecture walkthrough.
 *
 * Explains each platform layer through business and technical lenses with runtime evidence.
 */
function ArchitectureStoryboard({
  domain,
  persona,
  result,
  runtimeConfig,
  health,
  streamInspection,
  models,
  setPage,
}: {
  domain: DomainConfig;
  persona: Persona;
  result: PlaybookResult | null;
  runtimeConfig: RuntimeConfig | null;
  health: HealthPayload | null;
  streamInspection: StreamInspection | null;
  models: ModelVersion[];
  setPage: (page: Page) => void;
}) {
  const [selectedLayer, setSelectedLayer] = useState(0);
  const layer = architectureLayers[selectedLayer];
  const layerEvent = result?.layer_events.find((event) => event.layer === layer.id);
  const eventCount = result?.layer_events.length || platformLayers.length;
  const contract = architectureContract(layer.id);
  const runtime = architectureRuntimePath(layer.id, runtimeConfig, health, streamInspection);
  const liveEvidence = architectureLiveEvidence(layer.id, result, streamInspection, health, models);
  const touchpoints = architectureAppTouchpoints(layer.id);

  function moveLayer(direction: number) {
    setSelectedLayer((current) => Math.min(Math.max(current + direction, 0), architectureLayers.length - 1));
  }

  return (
    <>
      <header className="page-head">
        <div className="page-title">
          <p className="eyebrow">Architecture Storyboard</p>
          <h1>{domain.label} architecture walkthrough</h1>
          <p>
            The same decision flow explained as L0-L9 platform layers, with a business view and a technical view for
            each step.
          </p>
          <div className="tag-row">
            <span className="tag blue">{domain.caseType}</span>
            <span className="tag">{domain.jurisdiction}</span>
            <span className="tag green">{personaLabels[persona]} view</span>
          </div>
        </div>
        <aside className="outcome-card">
          <div className="outcome-top">
            <div>
              <p className="eyebrow">Current Layer</p>
              <h2>
                {layer.id} {layer.name}
              </h2>
            </div>
            <span className="tag amber">{layer.owner}</span>
          </div>
          <div className="metrics">
            <Metric label="Output" value={layer.output} />
            <Metric label="Events" value={eventCount} />
            <Metric label="Run" value={result?.run?.submission_id || 'Sample'} />
          </div>
        </aside>
      </header>

      <ArchitectureStoryPicture
        domain={domain}
        result={result}
        runtimeConfig={runtimeConfig}
        selectedLayer={layer.id}
        setSelectedLayer={setSelectedLayer}
      />

      <section className="architecture-flow" aria-label="Architecture layers">
        {architectureLayers.map((item, index) => (
          <button
            className={classNames([
              'architecture-tile',
              index < selectedLayer && 'complete',
              index === selectedLayer && 'active',
            ])}
            key={item.id}
            onClick={() => setSelectedLayer(index)}
          >
            <span>{item.id}</span>
            <strong>{item.name}</strong>
            <small>{item.short}</small>
          </button>
        ))}
      </section>

      <section className="architecture-workspace">
        <Panel title="Storyboard steps" tag={`${selectedLayer + 1} of ${architectureLayers.length}`}>
          <div className="architecture-step-list">
            {architectureLayers.map((item, index) => (
              <button
                className={classNames(['architecture-step-button', index === selectedLayer && 'active'])}
                key={item.id}
                onClick={() => setSelectedLayer(index)}
              >
                <span>{item.id}</span>
                <div>
                  <strong>{item.short}</strong>
                  <small>{item.summary}</small>
                </div>
              </button>
            ))}
          </div>
        </Panel>

        <article className="panel architecture-detail">
          <div className="story-hero">
            <div>
              <p className="eyebrow">{layer.output}</p>
              <h2>
                {layer.id}: {layer.name}
              </h2>
              <p>{layer.summary}</p>
            </div>
            <div className="hero-facts">
              <Fact label="Layer owner" value={layer.owner} />
              <Fact label="Execution status" value={layerEvent?.status || 'Designed'} />
              <Fact label="Layer event" value={layerEvent?.detail || layer.short} />
            </div>
          </div>

          <div className="persona-grid">
            <PersonaLens
              className="business-lens"
              title="Business View"
              tag="Story"
              body={layer.business}
              bullets={layer.businessBullets}
            />
            <PersonaLens
              className="technical-lens"
              title="Technical View"
              tag="Implementation"
              body={layer.technical}
              bullets={layer.technicalBullets}
            />
          </div>

          <div className="evidence-grid architecture-evidence">
            {layer.evidence.map(([title, status, detail]) => (
              <div className="evidence-card" key={`${layer.id}-${title}`}>
                <span>{title}</span>
                <strong>{status}</strong>
                <p>{detail}</p>
              </div>
            ))}
          </div>
        </article>

        <aside className="side-stack">
          <Panel title="Contract" tag={contract.produces}>
            <div className="mini-list">
              <div className="mini-row">
                <strong>Produces</strong>
                <span>{contract.produces}</span>
              </div>
              <div className="mini-row">
                <strong>Consumes</strong>
                <span>{contract.consumes}</span>
              </div>
              <div className="mini-row">
                <strong>Invariant</strong>
                <span>{contract.invariant}</span>
              </div>
              <div className="mini-row">
                <strong>Boundary</strong>
                <span>{contract.boundary}</span>
              </div>
            </div>
          </Panel>

          <Panel title="Runtime path" tag={runtime.mode}>
            <div className="mini-list">
              {runtime.rows.map(([label, value]) => (
                <div className="mini-row" key={`${layer.id}-${label}`}>
                  <strong>{label}</strong>
                  <span>{value}</span>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Live evidence" tag={liveEvidence.status}>
            <div className="mini-list">
              {liveEvidence.rows.map(([label, value]) => (
                <div className="mini-row" key={`${layer.id}-${label}`}>
                  <strong>{label}</strong>
                  <span>{value}</span>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Inspect in app" tag="Links">
            <div className="action-list">
              {touchpoints.map((item) => (
                <button
                  className={classNames(['action-button', item.primary && 'primary'])}
                  key={item.label}
                  onClick={() => setPage(item.page)}
                >
                  {item.label} <span>{item.target}</span>
                </button>
              ))}
            </div>
          </Panel>

          <Panel title="Domain mapping" tag={domain.label}>
            <div className="mini-list">
              {architectureDomainMapping(domain).map(([label, value]) => (
                <div className="mini-row" key={label}>
                  <strong>{label}</strong>
                  <span>{value}</span>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Next explanation" tag="Walkthrough">
            <div className="action-list">
              <button className="action-button" onClick={() => moveLayer(-1)} disabled={selectedLayer === 0}>
                Previous layer <span>{selectedLayer === 0 ? 'Start' : architectureLayers[selectedLayer - 1].id}</span>
              </button>
              <button
                className="action-button primary"
                onClick={() => moveLayer(1)}
                disabled={selectedLayer === architectureLayers.length - 1}
              >
                Next layer
                <span>
                  {selectedLayer === architectureLayers.length - 1
                    ? 'Complete'
                    : architectureLayers[selectedLayer + 1].id}
                </span>
              </button>
            </div>
          </Panel>
        </aside>
      </section>
    </>
  );
}

/**
 * Runtime settings page.
 *
 * Surfaces mock/local/live modes, local service links, stream inspection, and model routing
 * defaults supported by the backend configuration API.
 */
function SettingsPage({
  runtimeConfig,
  health,
  streamInspection,
  isBusy,
  onApply,
  onRefresh,
}: {
  runtimeConfig: RuntimeConfig | null;
  health: HealthPayload | null;
  streamInspection: StreamInspection | null;
  isBusy: boolean;
  onApply: (payload: RuntimeConfigPayload) => Promise<void>;
  onRefresh: () => void;
}) {
  const [appMode, setAppMode] = useState<RuntimeMode>('local_sync');
  const [llmProvider, setLlmProvider] = useState('ollama');
  const [llmModel, setLlmModel] = useState('llama3.1');
  const effective = runtimeConfig?.effective_llm_provider;
  const overrides = runtimeConfig?.runtime_overrides || {};
  const providerOptions = settingsProviderOptions(appMode);

  useEffect(() => {
    if (!runtimeConfig) return;
    const mode = supportedRuntimeMode(runtimeConfig.app_mode);
    const defaults = settingsDefaultsForMode(runtimeConfig, mode);
    const provider = supportedProviderForMode(mode, runtimeConfig.llm_provider || defaults.llmProvider);
    setAppMode(mode);
    setLlmProvider(provider);
    setLlmModel(defaultModelForProvider(runtimeConfig, provider, runtimeConfig.llm_model || defaults.llmModel));
  }, [runtimeConfig]);

  function changeAppMode(mode: RuntimeMode) {
    const defaults = settingsDefaultsForMode(runtimeConfig, mode);
    setAppMode(mode);
    setLlmProvider(defaults.llmProvider);
    setLlmModel(defaults.llmModel);
  }

  function changeProvider(provider: string) {
    setLlmProvider(provider);
    setLlmModel(defaultModelForProvider(runtimeConfig, provider));
  }

  function applySelectedSettings() {
    return onApply({
      app_mode: appMode,
      llm_provider: llmProvider,
      llm_model: llmProvider === 'mock' ? 'mock' : llmModel,
    });
  }

  return (
    <>
      <header className="page-head">
        <div className="page-title">
          <p className="eyebrow">Settings</p>
          <h1>Runtime control center</h1>
          <p>Process-level controls for mock mode, provider routing, local services, model registry, and defaults.</p>
          <div className="tag-row">
            <span className="tag blue">Mode: {runtimeConfig?.app_mode || 'loading'}</span>
            <span className={classNames(['tag', effective?.enabled ? 'green' : 'amber'])}>
              LLM: {effective?.provider || 'unknown'}
            </span>
            <span className="tag">{Object.keys(overrides).length} overrides</span>
          </div>
        </div>
        <aside className="outcome-card">
          <div className="outcome-top">
            <div>
              <p className="eyebrow">Effective Runtime</p>
              <h2>{runtimeConfig?.app_mode === 'mock' ? 'Mock only' : runtimeConfig?.app_mode || 'Loading'}</h2>
            </div>
            <span className={classNames(['tag', health?.status === 'healthy' ? 'green' : 'amber'])}>
              {health?.status || 'unknown'}
            </span>
          </div>
          <div className="metrics">
            <Metric label="LLM" value={effective?.provider || 'unknown'} />
            <Metric label="Data" value={health?.checks.db || 'unknown'} />
            <Metric label="Stream" value={health?.checks.redis || 'unknown'} />
          </div>
        </aside>
      </header>

      <section className="settings-grid">
        <Panel title="Runtime mode" tag="Control">
          <div className="settings-control">
            <label>
              <span>Application mode</span>
              <select value={appMode} onChange={(event) => changeAppMode(event.target.value as RuntimeMode)}>
                <option value="mock">Mock only</option>
                <option value="local_sync">Local sync</option>
                <option value="real">Live services</option>
              </select>
            </label>
            <label>
              <span>LLM provider</span>
              <select value={llmProvider} onChange={(event) => changeProvider(event.target.value)} disabled={appMode === 'mock'}>
                {providerOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>LLM model</span>
              <input
                value={llmModel}
                onChange={(event) => setLlmModel(event.target.value)}
                disabled={llmProvider === 'mock' || llmProvider === 'auto'}
                placeholder="Provider model name"
              />
            </label>
            <div className="settings-hint">
              {settingsModeDescription(appMode, llmProvider, llmModel)}
            </div>
          </div>
          <div className="action-list settings-actions">
            <button className="action-button primary" onClick={applySelectedSettings} disabled={isBusy}>
              {settingsApplyLabel(appMode)} <span>{isBusy ? 'Saving' : 'Apply'}</span>
            </button>
            <button className="action-button" onClick={onRefresh} disabled={isBusy}>
              Refresh settings <RefreshCw size={14} className={isBusy ? 'spin' : ''} />
            </button>
          </div>
        </Panel>

        <Panel title="Provider readiness" tag={effective?.enabled ? 'Ready' : 'Fallback'}>
          <div className="settings-status">
            <div className="action-outcome compact">
              <span>Effective LLM</span>
              <strong>{effective?.model || 'mock'}</strong>
              <p>{effective?.reason || 'Configuration is loading.'}</p>
            </div>
            <div className="mini-list">
              <div className="mini-row"><strong>Auto provider</strong><span>{runtimeConfig?.llm_provider_status.selected || 'unknown'}</span></div>
              <div className="mini-row"><strong>Ollama endpoint</strong><span>{runtimeConfig?.ollama_base_url || 'not set'}</span></div>
              <div className="mini-row"><strong>OpenAI key</strong><span>{runtimeConfig?.llm_provider_status.openai_configured ? 'configured' : 'not configured'}</span></div>
              <div className="mini-row"><strong>Anthropic key</strong><span>{runtimeConfig?.llm_provider_status.anthropic_configured ? 'configured' : 'not configured'}</span></div>
              <div className="mini-row"><strong>Custom key</strong><span>{runtimeConfig?.llm_provider_status.custom_configured ? 'configured' : 'not configured'}</span></div>
            </div>
          </div>
        </Panel>

        <Panel title="Local services" tag={health?.status || 'unknown'}>
          <div className="settings-service-list">
            <ServiceRow icon={<Database size={16} />} label="Database" status={health?.checks.db || 'unknown'} detail={runtimeConfig?.database_url || 'loading'} />
            <ServiceRow icon={<GitBranch size={16} />} label="Stream" status={health?.checks.redis || 'unknown'} detail={runtimeConfig?.redis_url || 'not configured'} />
            <ServiceRow
              icon={<ServerCog size={16} />}
              label="MLflow"
              status={health?.checks.mlflow || 'unknown'}
              detail={runtimeConfig?.mlflow_tracking_uri || 'loading'}
              href={httpUrl(runtimeConfig?.mlflow_tracking_uri)}
            />
            <ServiceRow
              icon={<Layers3 size={16} />}
              label="Telemetry"
              status="configured"
              detail={runtimeConfig?.jaeger_endpoint || 'loading'}
              href={telemetryUiUrl(runtimeConfig?.jaeger_endpoint)}
            />
          </div>
        </Panel>

        <Panel title="Defaults and overrides" tag="Process">
          <div className="mini-list">
            <div className="mini-row"><strong>Default domain</strong><span>{runtimeConfig?.default_domain || 'loading'}</span></div>
            <div className="mini-row"><strong>Default jurisdiction</strong><span>{runtimeConfig?.default_jurisdiction || 'loading'}</span></div>
            <div className="mini-row"><strong>Runtime overrides</strong><span>{Object.keys(overrides).length ? Object.keys(overrides).join(', ') : 'none'}</span></div>
            <div className="mini-row"><strong>Config source</strong><span>environment plus process overrides</span></div>
          </div>
        </Panel>

        <Panel title="Stream inspector" tag={streamInspection?.backend || 'loading'}>
          <div className="stream-inspector">
            <div className="action-outcome compact">
              <span>Input stream</span>
              <strong>{streamInspection?.stream_name || 'loading'}</strong>
              <p>{streamInspection?.status || 'Stream inspection is loading.'}</p>
            </div>
            <div className="mini-list">
              <div className="mini-row"><strong>Consumer group</strong><span>{streamInspection?.consumer_group || 'loading'}</span></div>
              <div className="mini-row"><strong>Recent inputs</strong><span>{streamInspection?.input_count ?? 0}</span></div>
              <div className="mini-row"><strong>Pending</strong><span>{streamInspection?.pending_count ?? 0}</span></div>
              <div className="mini-row"><strong>DLQ outputs</strong><span>{streamInspection?.dlq_count ?? 0}</span></div>
            </div>
            <div className="stream-entry-list">
              {(streamInspection?.recent_inputs.length ? streamInspection.recent_inputs : []).map((entry) => (
                <div className="stream-entry" key={entry.message_id}>
                  <strong>{entry.message_id}</strong>
                  <span>{entry.submission_id}</span>
                  <small>{entry.case_type} from {entry.source_channel}</small>
                </div>
              ))}
              {streamInspection && !streamInspection.recent_inputs.length && (
                <div className="settings-hint">No recent stream inputs are available for this domain.</div>
              )}
            </div>
            <p className="stream-note">{streamInspection?.output_note}</p>
          </div>
        </Panel>
      </section>
    </>
  );
}

/**
 * Operational snapshot for health checks, registry state, and latest run telemetry.
 */
function Operations({ domain, health, models, result }: { domain: DomainConfig; health: HealthPayload | null; models: ModelVersion[]; result: PlaybookResult | null }) {
  return (
    <>
      <header className="page-head single">
        <div className="page-title">
          <p className="eyebrow">Operations</p>
          <h1>Technical platform map</h1>
          <p>The same {domain.label.toLowerCase()} business flow mapped to the L0-L9 architecture and runtime posture.</p>
        </div>
      </header>
      <section className="panel platform-map">
        <div className="panel-head">
          <h2>L0-L9 execution layers</h2>
          <span className="tag blue">{result?.layer_events.length || platformLayers.length} events</span>
        </div>
        <div className="panel-body layer-grid">
          {platformLayers.map((layer) => (
            <div className="layer-card" key={layer[0]}>
              <span>{layer[0]}</span>
              <strong>{layer[1]}</strong>
              <small>{layer[2]}</small>
            </div>
          ))}
        </div>
      </section>
      <section className="ops-grid">
        <Panel title="Service health" tag={health?.status || 'unknown'}>
          <div className="mini-list">
            {Object.entries(health?.checks || {}).map(([key, value]) => (
              <div className="mini-row" key={key}>
                <strong>{key}</strong>
                <span>{value}</span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Model registry" tag={`${models.length} models`}>
          <div className="mini-list">
            {models.slice(0, 5).map((model) => (
              <div className="mini-row" key={`${model.model_name}-${model.version}`}>
                <strong>{model.model_name}</strong>
                <span>{model.stage}</span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Runtime mode" tag="Config">
          <div className="mini-list">
            <div className="mini-row"><strong>LLM</strong><span>Mock default</span></div>
            <div className="mini-row"><strong>Connectors</strong><span>Config-gated</span></div>
            <div className="mini-row"><strong>Audit</strong><span>Append-only</span></div>
          </div>
        </Panel>
      </section>
    </>
  );
}

/**
 * Map the selected business domain to architecture-layer ownership notes.
 */
function architectureDomainMapping(domain: DomainConfig): Array<[string, string]> {
  const mappings: Record<DomainKey, Array<[string, string]>> = {
    insurance: [
      ['Triage', 'Submission completeness and jurisdiction'],
      ['Scoring', 'Exposure, property risk, claims context'],
      ['Decision', 'Approve, refer, or decline'],
      ['Review', 'Underwriter action and audit package'],
    ],
    lending: [
      ['Triage', 'Application completeness and eligibility'],
      ['Scoring', 'Credit risk and affordability'],
      ['Decision', 'Approve, condition, or decline'],
      ['Review', 'Loan officer action and notice package'],
    ],
    healthcare: [
      ['Triage', 'Request, diagnosis, and service validation'],
      ['Scoring', 'Criteria match and medical necessity'],
      ['Decision', 'Approve, pend, or clinical review'],
      ['Review', 'Reviewer action and determination package'],
    ],
    wealth: [
      ['Triage', 'Client profile and product request'],
      ['Scoring', 'Suitability, liquidity, and risk fit'],
      ['Decision', 'Suitable, review, or not suitable'],
      ['Review', 'Advisor action and compliance archive'],
    ],
  };
  return mappings[domain.key];
}

/**
 * Return the platform contract enforced by a given architecture layer.
 */
function architectureContract(layerId: string) {
  const contracts: Record<string, { produces: string; consumes: string; invariant: string; boundary: string }> = {
    L0: {
      produces: 'SubmissionEvent',
      consumes: 'Playbook YAML',
      invariant: 'Schema-valid request',
      boundary: 'API receives typed payload',
    },
    L1: {
      produces: 'Stream position',
      consumes: 'SubmissionEvent',
      invariant: 'At-least-once input visibility',
      boundary: 'Queue stores event JSON',
    },
    L2: {
      produces: 'Agent sequence',
      consumes: 'SubmissionEvent',
      invariant: 'Domain logic stays in domains',
      boundary: 'Shared orchestrator uses adapters',
    },
    L3: {
      produces: 'AgentOutput',
      consumes: 'UnifiedContext',
      invariant: 'Explanation is required',
      boundary: 'Agents return typed records',
    },
    L4: {
      produces: 'UnifiedContext',
      consumes: 'Connector results',
      invariant: 'Sources tracked as available/missing',
      boundary: 'MCP data normalized',
    },
    L5: {
      produces: 'WorkbenchCase',
      consumes: 'Recommendation and flags',
      invariant: 'Human actions append audit',
      boundary: 'Reviewer state is typed',
    },
    L6: {
      produces: 'Analytics record',
      consumes: 'Audit and workbench records',
      invariant: 'Records persist before reporting',
      boundary: 'Local or PostgreSQL store',
    },
    L7: {
      produces: 'ScoringResult',
      consumes: 'Model metadata and features',
      invariant: 'Model version captured',
      boundary: 'MLflow registry facade',
    },
    L8: {
      produces: 'Telemetry event',
      consumes: 'Runtime checks and spans',
      invariant: 'Health and latency visible',
      boundary: 'Metrics and tracing endpoints',
    },
    L9: {
      produces: 'AuditRecord',
      consumes: 'Governance result',
      invariant: 'Append-only audit trail',
      boundary: 'No update/delete path',
    },
  };
  return contracts[layerId] || contracts.L0;
}

/**
 * Describe the current runtime path for a layer using live configuration.
 */
function architectureRuntimePath(
  layerId: string,
  runtimeConfig: RuntimeConfig | null,
  health: HealthPayload | null,
  streamInspection: StreamInspection | null,
) {
  const mode = runtimeConfig?.app_mode || 'mock';
  const sharedRows: Array<[string, string]> = [
    ['Mode', mode],
    ['LLM', runtimeConfig?.effective_llm_provider.provider || 'mock'],
  ];
  const rowsByLayer: Record<string, Array<[string, string]>> = {
    L0: [['API', 'FastAPI validation'], ['Config', 'Default domain and jurisdiction']],
    L1: [
      ['Backend', streamInspection?.backend || 'memory'],
      ['Stream', streamInspection?.stream_name || 'submissions:{domain}'],
    ],
    L2: [['Runtime', 'LangGraph orchestrator'], ['Adapter', 'Domain registry']],
    L3: [['LLM path', runtimeConfig?.effective_llm_provider.reason || 'mock fallback']],
    L4: [['MCP path', mode === 'real' ? 'config-gated connectors' : 'mock fixtures']],
    L5: [['Queue', 'Workbench persistence'], ['Review', 'human action appends audit']],
    L6: [['Database', health?.checks.db || 'unknown'], ['Analytics', 'persisted summary views']],
    L7: [['Registry', health?.checks.mlflow || 'unknown'], ['Fallback', 'deterministic scorer']],
    L8: [['Health', health?.status || 'unknown'], ['Telemetry', runtimeConfig?.jaeger_endpoint || 'unset']],
    L9: [['Audit', 'append-only'], ['Governance', 'policy rules sealed']],
  };
  return { mode, rows: [...sharedRows, ...(rowsByLayer[layerId] || rowsByLayer.L0)] };
}

/**
 * Summarize live evidence shown in the architecture walkthrough.
 */
function architectureLiveEvidence(
  layerId: string,
  result: PlaybookResult | null,
  streamInspection: StreamInspection | null,
  health: HealthPayload | null,
  models: ModelVersion[],
) {
  const layerEvent = result?.layer_events.find((event) => event.layer === layerId);
  const runId = result?.run?.submission_id || 'no run selected';
  const rowsByLayer: Record<string, Array<[string, string | number]>> = {
    L0: [['Run', runId], ['Playbook', result?.run?.playbook_name || 'sample only']],
    L1: [
      ['Inputs', streamInspection?.input_count ?? 0],
      ['Pending', streamInspection?.pending_count ?? 0],
      ['DLQ', streamInspection?.dlq_count ?? 0],
    ],
    L2: [['Layer event', layerEvent?.detail || 'designed state'], ['Status', layerEvent?.status || 'none']],
    L3: [['Rule events', result?.rule_events.length || 0], ['Status', layerEvent?.status || 'none']],
    L4: [['Evidence cards', result?.rule_events.length || 3], ['Status', layerEvent?.status || 'none']],
    L5: [['Outcome', result?.run?.final_decision || 'sample outcome'], ['Status', layerEvent?.status || 'none']],
    L6: [['Health', health?.status || 'unknown'], ['Database', health?.checks.db || 'unknown']],
    L7: [['Registered models', models.length], ['MLflow', health?.checks.mlflow || 'unknown']],
    L8: [['API', health?.checks.api || 'unknown'], ['Stream', health?.checks.redis || 'unknown']],
    L9: [['Audit records', result?.audit_records.length || 0], ['Status', layerEvent?.status || 'none']],
  };
  const rows = (rowsByLayer[layerId] || rowsByLayer.L0).map(([label, value]) => [
    label,
    String(value),
  ] as [string, string]);
  return { status: layerEvent?.status || (result ? 'available' : 'sample'), rows };
}

/**
 * Connect architecture layers back to the UI surface that exercises them.
 */
function architectureAppTouchpoints(layerId: string) {
  const touchpoints: Record<string, Array<{ label: string; target: string; page: Page; primary?: boolean }>> = {
    L0: [
      { label: 'Open Playbook Studio', target: 'Studio', page: 'studio', primary: true },
      { label: 'View audit trace', target: 'Audit', page: 'audit' },
    ],
    L1: [
      { label: 'Open Stream inspector', target: 'Settings', page: 'settings', primary: true },
      { label: 'View operations health', target: 'Ops', page: 'operations' },
    ],
    L2: [
      { label: 'View operations map', target: 'Ops', page: 'operations', primary: true },
      { label: 'Run Playbook', target: 'Studio', page: 'studio' },
    ],
    L3: [
      { label: 'Open decision workspace', target: 'Workspace', page: 'workspace', primary: true },
      { label: 'View trace package', target: 'Audit', page: 'audit' },
    ],
    L4: [
      { label: 'Open evidence view', target: 'Workspace', page: 'workspace', primary: true },
      { label: 'Check connectors', target: 'Settings', page: 'settings' },
    ],
    L5: [
      { label: 'Open review queue', target: 'Queue', page: 'queue', primary: true },
      { label: 'View audit output', target: 'Audit', page: 'audit' },
    ],
    L6: [
      { label: 'Open audit reports', target: 'Audit', page: 'audit', primary: true },
      { label: 'View operations', target: 'Ops', page: 'operations' },
    ],
    L7: [
      { label: 'Open model registry', target: 'Ops', page: 'operations', primary: true },
      { label: 'Check settings', target: 'Settings', page: 'settings' },
    ],
    L8: [
      { label: 'Open operations', target: 'Ops', page: 'operations', primary: true },
      { label: 'Open settings', target: 'Settings', page: 'settings' },
    ],
    L9: [
      { label: 'Open audit package', target: 'Audit', page: 'audit', primary: true },
      { label: 'Open review queue', target: 'Queue', page: 'queue' },
    ],
  };
  return touchpoints[layerId] || touchpoints.L0;
}

/**
 * Coerce backend runtime-mode values into modes supported by the UI controls.
 */
function supportedRuntimeMode(value: string): RuntimeMode {
  return value === 'real' || value === 'local_sync' || value === 'mock' ? value : 'mock';
}

/**
 * Return valid LLM provider choices for the selected runtime mode.
 */
function settingsProviderOptions(mode: RuntimeMode) {
  if (mode === 'mock') {
    return [{ value: 'mock', label: 'Mock' }];
  }
  if (mode === 'local_sync') {
    return [
      { value: 'ollama', label: 'Ollama' },
      { value: 'mock', label: 'Mock' },
    ];
  }
  return [
    { value: 'auto', label: 'Auto' },
    { value: 'openai', label: 'OpenAI compatible' },
    { value: 'anthropic', label: 'Anthropic compatible' },
    { value: 'ollama', label: 'Ollama' },
    { value: 'mock', label: 'Mock' },
  ];
}

/**
 * Derive settings form defaults from the active runtime configuration.
 */
function settingsDefaultsForMode(runtimeConfig: RuntimeConfig | null, mode: RuntimeMode) {
  if (mode === 'mock') {
    return { llmProvider: 'mock', llmModel: 'mock' };
  }
  if (mode === 'local_sync') {
    return { llmProvider: 'ollama', llmModel: runtimeConfig?.ollama_model || 'llama3.1' };
  }
  return { llmProvider: 'auto', llmModel: runtimeConfig?.llm_model || '' };
}

/**
 * Decide whether a provider is available for the selected runtime mode.
 */
function supportedProviderForMode(mode: RuntimeMode, provider: string) {
  const supported = settingsProviderOptions(mode).map((option) => option.value);
  if (supported.includes(provider)) return provider;
  return settingsDefaultsForMode(null, mode).llmProvider;
}

/**
 * Pick the configured default model for a provider while preserving manual input.
 */
function defaultModelForProvider(runtimeConfig: RuntimeConfig | null, provider: string, current = '') {
  if (provider === 'mock') return 'mock';
  if (provider === 'ollama') {
    return current && current !== 'mock' ? current : runtimeConfig?.ollama_model || 'llama3.1';
  }
  if (provider === 'openai') {
    return current && current !== 'mock' ? current : runtimeConfig?.openai_model || 'openai/gpt-4o-mini';
  }
  if (provider === 'anthropic') {
    return current && current !== 'mock' ? current : runtimeConfig?.anthropic_model || 'anthropic/claude-sonnet-4-6';
  }
  return provider === 'auto' ? '' : current;
}

/**
 * Explain the effective provider/model route shown in settings.
 */
function settingsModeDescription(mode: RuntimeMode, provider: string, model: string) {
  if (mode === 'mock') {
    return 'Mock only uses deterministic local agents, mock connectors, local persistence, and no external LLM calls.';
  }
  if (mode === 'local_sync') {
    return provider === 'ollama'
      ? `Local sync uses local services and routes LLM rationale to Ollama model ${model}.`
      : 'Local sync keeps local services active while retaining deterministic mock LLM behavior.';
  }
  if (provider === 'auto') {
    return 'Live services use configured provider keys in priority order and fall back when none are configured.';
  }
  return `Live services route LLM rationale to ${provider} with model ${model || 'from environment'}.`;
}

/**
 * Return the submit button label for the active runtime mode.
 */
function settingsApplyLabel(mode: RuntimeMode) {
  if (mode === 'mock') return 'Apply mock-only runtime';
  if (mode === 'local_sync') return 'Apply local-sync runtime';
  return 'Apply live-services runtime';
}

/**
 * Normalize service endpoints into browser-openable URLs.
 */
function httpUrl(value: string | null | undefined) {
  if (!value?.startsWith('http://') && !value?.startsWith('https://')) return undefined;
  return value;
}

/**
 * Convert collector endpoints into the expected telemetry UI URL.
 */
function telemetryUiUrl(endpoint: string | null | undefined) {
  const url = httpUrl(endpoint);
  if (!url) return undefined;
  try {
    const parsed = new URL(url);
    if (parsed.port === '4317' || parsed.port === '4318') {
      parsed.port = '16686';
    }
    parsed.pathname = '';
    parsed.search = '';
    parsed.hash = '';
    return parsed.toString();
  } catch {
    return undefined;
  }
}

/**
 * Render one service-health row with link and status treatment.
 */
function ServiceRow({
  icon,
  label,
  status,
  detail,
  href,
}: {
  icon: React.ReactNode;
  label: string;
  status: string;
  detail: string;
  href?: string;
}) {
  const content = (
    <>
      <span className="service-icon">{icon}</span>
      <div>
        <strong>{label}</strong>
        <small>{detail}</small>
      </div>
      <span className="service-state">
        <span className={classNames(['tag', status.startsWith('error') ? 'amber' : 'green'])}>{status}</span>
        {href && <ExternalLink size={14} />}
      </span>
    </>
  );

  return href ? (
    <a className="service-row service-row-link" href={href} target="_blank" rel="noreferrer">
      {content}
    </a>
  ) : (
    <div className="service-row">{content}</div>
  );
}

/**
 * Shared framed section used by operational and architecture detail panels.
 */
function Panel({ title, tag, children }: { title: string; tag: string; children: React.ReactNode }) {
  return (
    <article className="panel">
      <div className="panel-head">
        <h3>{title}</h3>
        <span className="tag blue">{tag}</span>
      </div>
      <div className="panel-body">{children}</div>
    </article>
  );
}

/**
 * Compact KPI tile for dashboard and run metrics.
 */
function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

/**
 * Label-value block for dense facts inside larger panels.
 */
function Fact({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="hero-fact">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

/**
 * Inline label-value row for timelines and technical evidence lists.
 */
function FactRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="fact-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

/**
 * Persona-specific narrative panel for business and technical views.
 */
function PersonaLens({ className, title, tag, body, bullets }: { className: string; title: string; tag: string; body: string; bullets: string[] }) {
  return (
    <section className={classNames(['lens', className])}>
      <h3>
        {title}
        <span className="tag green">{tag}</span>
      </h3>
      <div className="lens-content">
        <p>{body}</p>
        <ul className="bullet-list">
          {bullets.map((item) => (
            <li key={item}>
              <span className="dot" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/**
 * Render structured Playbook validation messages with severity treatment.
 */
function MessageList({ messages }: { messages: ValidationMessage[] }) {
  if (!messages.length) {
    return (
      <div className="message-row ok">
        <CheckCircle2 size={16} />
        <span>No blocking validation findings.</span>
      </div>
    );
  }
  return (
    <div className="message-list">
      {messages.map((message) => (
        <div className={classNames(['message-row', message.severity])} key={`${message.field}-${message.code}`}>
          {message.severity === 'error' ? <XCircle size={16} /> : <AlertTriangle size={16} />}
          <div>
            <strong>{message.field}</strong>
            <span>{message.message}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Return the business-facing copy for a domain/stage pair.
 */
function businessNarrative(domain: DomainConfig, stage: number) {
  const names = [
    `The ${domain.label.toLowerCase()} case is captured and ready for evaluation.`,
    'Evidence has been gathered so the decision is not based only on the uploaded form.',
    `${domain.outcome} because the decision logic found a material business reason that needs attention.`,
    'Governance rules have wrapped the recommendation and converted policy into clear review requirements.',
    `The case is ready for the ${domain.queue.toLowerCase()} with reasons, evidence, and actions.`,
    'The decision package is ready for customer, reviewer, or regulator reconstruction.',
  ];
  return names[stage] || names[0];
}

/**
 * Return business-facing bullets for a domain/stage pair.
 */
function businessBullets(domain: DomainConfig, stage: number) {
  const shared = [
    ['Domain language is used instead of platform internals.', `The selected workflow is ${domain.caseType}.`, `Jurisdiction is ${domain.jurisdiction}.`],
    ['Context sources are summarized in business terms.', 'Missing evidence would trigger review.', 'The case remains traceable by run ID.'],
    ['The recommendation is expressed as an actionable outcome.', 'Confidence and threshold posture are visible.', 'The reason can be explained to a reviewer.'],
    ['Policy rules are translated into reason codes.', 'Prohibited factors are not used.', 'Required notices and disclosures are attached.'],
    ['Reviewer actions are explicit.', 'Evidence is organized by decision factor.', 'Human notes append to the audit trail.'],
    ['Decision report is downloadable.', 'Audit package includes rules and evidence.', 'Trace packet is available for technical review.'],
  ];
  return shared[stage] || shared[0];
}

/**
 * Return the technical explanation for a domain/stage pair.
 */
function technicalNarrative(domain: DomainConfig, stage: number) {
  const names = [
    `A typed SubmissionEvent is routed to the ${domain.key} domain adapter.`,
    'MCP context assembly returns source availability and evidence payloads.',
    'AgentOutput records capture decision, confidence, evidence, flags, and explanation.',
    'GovernanceEvaluationResult records rules applied, violations, escalation state, and timestamp.',
    'WorkbenchCase stores recommendation, escalation reason, and reviewer state.',
    'AuditRecord entries are append-only and can reconstruct the run.',
  ];
  return names[stage] || names[0];
}

/**
 * Return technical bullets, adding live run evidence when available.
 */
function technicalBullets(domain: DomainConfig, stage: number, result: PlaybookResult | null) {
  const stageEvent = result?.layer_events[stage];
  const shared = [
    [`domain: ${domain.key}`, `case_type: ${domain.caseType}`, 'source_channel: playbook_upload'],
    ['sources_available recorded', 'context_confidence computed', 'payload persisted for trace'],
    ['agent_id and agent_type recorded', 'confidence in range 0..1', 'explanation required by schema'],
    ['rules_applied list persisted', 'escalation_triggered captured', 'audit writer receives governance result'],
    ['status: pending/in_review/decided', 'human decision appends another audit record', 'no destructive audit path'],
    ['decision_type captured', 'agent_outputs serialized as typed records', 'layer events are available through API'],
  ];
  return stageEvent ? [`${stageEvent.layer}: ${stageEvent.name}`, stageEvent.detail, `status: ${stageEvent.status}`] : shared[stage] || shared[0];
}

/**
 * Build the evidence cards shown for the selected stage.
 */
function evidenceCards(domain: DomainConfig, stage: number, result: PlaybookResult | null): Array<[string, string, string]> {
  if (result?.rule_events.length && stage >= 3) {
    return result.rule_events.slice(0, 3).map((event) => [event.rule_field, event.result, event.display]);
  }
  const byStage: Array<Array<[string, string, string]>> = [
    [['Input', 'Normalized', `${domain.caseType} details captured.`], ['Jurisdiction', domain.jurisdiction, 'Policy context selected.'], ['Run', 'Traceable', 'Submission ID created.']],
    [['Core data', 'Available', 'Internal evidence attached.'], ['History', 'Available', 'Prior activity retrieved.'], ['External data', 'Available', 'Risk indicators available.']],
    [['Triage', 'Proceed', 'Enough evidence to evaluate.'], ['Risk', 'Reviewable', 'Confidence and thresholds checked.'], ['Decision', domain.outcome, 'Recommendation generated.']],
    [['Policy', 'Applied', 'Domain rules evaluated.'], ['Prohibited factors', 'Passed', 'Blocked fields not used.'], ['Audit', 'Ready', 'Governance result persisted.']],
    [['Queue', 'Pending', `Assigned to ${domain.queue}.`], ['Reason', domain.outcomeTag, 'Review trigger is explicit.'], ['Actions', 'Ready', 'Reviewer commands available.']],
    [['Report', 'Ready', 'Business summary available.'], ['Audit JSON', 'Ready', 'Full reconstruction payload available.'], ['Trace', 'Ready', 'Layer event timeline available.']],
  ];
  return byStage[stage] || byStage[0];
}

/**
 * Build available audit packages from latest run and workbench decisions.
 */
function auditPackageOptions(domain: DomainConfig, result: PlaybookResult | null, cases: WorkbenchCase[]) {
  const options: Array<{
    source: string;
    label: string;
    subtitle: string;
    summary: string;
    submissionId: string;
    caseId?: string;
    jurisdiction: string;
    confidence: string;
    status: string;
  }> = [];
  if (result?.run && result.run.domain === domain.key) {
    options.push({
      source: 'Run result',
      label: `Run ${result.run.submission_id.replaceAll('-', '').slice(0, 8).toUpperCase()}`,
      subtitle: `${caseTypeLabel(result.run.case_type)} · ${result.run.jurisdiction}`,
      summary: `${result.run.final_decision || domain.outcome} with ${result.audit_records.length} audit records and ${result.layer_events.length} layer events.`,
      submissionId: result.run.submission_id,
      jurisdiction: result.run.jurisdiction,
      confidence: domain.metricOne[1],
      status: result.run.final_decision ? 'Complete' : 'Generated',
    });
  }
  for (const item of cases) {
    if (options.some((option) => option.submissionId === item.submission.submission_id)) continue;
    options.push({
      source: item.status === 'decided' ? 'Reviewer action' : 'Review case',
      label: queueCaseLabel(domain, item),
      subtitle: `${caseTypeLabel(item.submission.case_type)} · ${item.submission.jurisdiction}`,
      summary: `${item.escalation_reason || domain.outcome}. Current reviewer status is ${item.status}.`,
      submissionId: item.submission.submission_id,
      caseId: item.case_id,
      jurisdiction: item.submission.jurisdiction,
      confidence: formatPercent(item.confidence),
      status: item.status,
    });
  }
  return options;
}

/**
 * Translate audit decision types into reviewer-friendly labels.
 */
function auditDecisionTypeLabel(value?: string) {
  if (!value) return 'Decision record';
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

/**
 * Build a short queue label that preserves domain context.
 */
function queueCaseLabel(domain: DomainConfig, item: WorkbenchCase) {
  const suffix = item.submission.submission_id.replaceAll('-', '').slice(0, 8).toUpperCase();
  const prefix = domain.key === 'insurance' ? 'UW' : domain.key === 'lending' ? 'CR' : domain.key === 'healthcare' ? 'PA' : 'SU';
  return `${prefix}-${suffix}`;
}

/**
 * Convert case-type ids into readable UI labels.
 */
function caseTypeLabel(value: string) {
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

/**
 * Convert agent-type ids into readable UI labels.
 */
function agentTypeLabel(value: string) {
  return caseTypeLabel(value.replaceAll('-', '_'));
}

/**
 * Format confidence values as whole-number percentages.
 */
function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

/**
 * Expand queue case flags into reviewer reason labels.
 */
function queueReviewReasons(item: WorkbenchCase) {
  const flags = item.agent_outputs.flatMap((agent) => agent.flags || []);
  const reasons = [
    item.escalation_reason || 'The recommendation requires human review.',
    `${caseTypeLabel(item.submission.case_type)} in ${item.submission.jurisdiction} requires reviewer visibility.`,
    `Recommendation confidence is ${formatPercent(item.confidence)}.`,
  ];
  return [...reasons, ...flags.slice(0, 3).map((flag) => `Agent flag: ${flag}`)];
}

/**
 * Build evidence cards for the selected reviewer case.
 */
function queueEvidenceCards(item: WorkbenchCase, domain: DomainConfig): Array<[string, string, string]> {
  const latestAgent = item.agent_outputs[item.agent_outputs.length - 1];
  const evidence = latestAgent?.evidence?.slice(0, 3).map((entry) => [
    agentTypeLabel(entry.source),
    String(entry.field),
    `${String(entry.value)} · ${formatPercent(entry.confidence)}`,
  ] as [string, string, string]) || [];
  if (evidence.length) return evidence;
  const available = item.context?.sources_available || [];
  return [
    ['Recommendation', item.agent_recommendation || domain.outcome, latestAgent?.explanation || domain.summary],
    ['Context', item.context?.context_confidence || 'Available', available.length ? available.join(', ') : 'Core evidence attached'],
    ['Review reason', domain.outcomeTag, item.escalation_reason || businessNarrative(domain, 4)],
  ];
}

/**
 * Return representative agent outputs when a queue case lacks persisted details.
 */
function sampleAgentOutputs(domain: DomainConfig): WorkbenchCase['agent_outputs'] {
  return [
    {
      agent_type: 'review',
      decision: domain.outcome,
      confidence: 0.71,
      explanation: `${domain.outcome} because the policy and evidence indicate reviewer attention is required before final action.`,
    },
  ];
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
