import {
  ChangeEvent,
  FormEvent,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
  LineChart,
  Line,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';

type Card = { label: string; value: string; note: string };

type LifecycleStage = {
  step: number;
  title: string;
  description: string;
  checks: string[];
  status: 'complete' | 'warning' | 'active';
};

type LedgerEntry = {
  block: number;
  artifact: string;
  event: string;
  hash: string;
  signer: string;
  timestamp: string;
  status: string;
  submission_id?: string;
  patient_id?: string;
  visit_id?: string;
};

type MetricPoint = { name: string; score: number };
type SeverityPoint = { severity: string; count: number };
type TrendPoint = { month: string; score: number };
type SourcePoint = { source: string; records: number };
type ReadinessItem = { criterion: string; status: string; detail: string };

type SourceFeed = {
  source: string;
  records: number;
  sites: number;
  countries: string;
  last_ingest: string;
  avg_dq: number;
  schema_status: string;
  integrity_status: string;
  linkage_status: string;
  feed_status: 'healthy' | 'warning' | 'pending';
  note: string;
};

type OmopSnapshot = {
  snapshot_id: string;
  snapshot_status: 'complete' | 'warning';
  mapping_coverage: number;
  vocabulary_coverage: number;
  quality_gate_pass_rate: number;
  snapshot_block: number | null;
};

type OmopRunContext = {
  run_id: string;
  etl_spec_version: string;
  vocabulary_release: string;
  target_cdm: string;
  last_run_at: string;
  status: 'complete' | 'warning';
};

type OmopDomainLoad = {
  domain: string;
  rows: number;
  note: string;
};

type OmopEtlSummary = {
  current_snapshot: OmopSnapshot;
  run_context: OmopRunContext;
  domain_loads: OmopDomainLoad[];
  mapping_gaps: string[];
};

type PermitRecord = {
  id: string;
  created_at: string;
  created_by: string;
  permit_id: string;
  requesting_organization: string;
  purpose_code: string;
  expiry_date: string;
  issuing_hdab: string;
  status: string;
  notes: string;
};

type PermitGate = {
  restricted: boolean;
  banner: string;
  active_permit: PermitRecord | null;
};

type DashboardPayload = {
  prototype: {
    name: string;
    subtitle: string;
    challenge: string[];
    regulatory_alignment: string[];
  };
  top_cards: Card[];
  source_feeds: SourceFeed[];
  omop_etl: OmopEtlSummary;
  permit_gate: PermitGate;
  data_lifecycle: LifecycleStage[];
  ledger: LedgerEntry[];
  quality: {
    dimensions: MetricPoint[];
    issue_severity: SeverityPoint[];
    readiness_trend: TrendPoint[];
    source_coverage: SourcePoint[];
    open_findings: string[];
  };
  trial_readiness: ReadinessItem[];
  next_steps: string[];
};

type Submission = {
  id: string;
  created_at: string;
  site_name: string;
  source_type: string;
  country: string;
  operator_id: string;
  record_count: number;
  hbv_cohort: number;
  bepirovirsen_treated: number;
  dq_score: number;
  readiness_score: number;
  schema_signed: boolean;
  temporal_issue_count: number;
  needs_vocab_remap: boolean;
  notes: string;
  file_name?: string | null;
  artifact_hash: string;
  ledger_block: number;
  verification_status: string;
};

type Visit = {
  id: string;
  patient_id: string;
  created_at: string;
  visit_date: string;
  visit_type: string;
  quantitative_hbsag: number | null;
  hbv_dna: number | null;
  hbv_dna_detectable: boolean;
  alt: number | null;
  ast: number | null;
  hbeag_status: string;
  bilirubin: number | null;
  albumin: number | null;
  inr: number | null;
  on_na_therapy: boolean;
  on_bepirovirsen: boolean;
  functional_cure_endpoint: boolean;
  notes: string;
  artifact_hash: string;
  ledger_block: number;
  verification_status: string;
};

type Patient = {
  id: string;
  created_at: string;
  site_name: string;
  country: string;
  operator_id: string;
  patient_pseudonym: string;
  sex: string;
  year_of_birth: number;
  diagnosis_date: string;
  chronic_hbv_confirmed: boolean;
  on_na_therapy: boolean;
  bepirovirsen_eligible: boolean;
  started_bepirovirsen: boolean;
  baseline_hbsag: number | null;
  baseline_hbv_dna: number | null;
  baseline_alt: number | null;
  baseline_ast: number | null;
  hbeag_status: string;
  bilirubin: number | null;
  albumin: number | null;
  inr: number | null;
  notes: string;
  artifact_hash: string;
  ledger_block: number;
  verification_status: string;
  visit_count: number;
  visits: Visit[];
};

type VerifyResponse = {
  verified: boolean;
  message: string;
  ledger_block: number;
};

type DatasetFormState = {
  site_name: string;
  source_type: string;
  country: string;
  operator_id: string;
  record_count: number;
  hbv_cohort: number;
  bepirovirsen_treated: number;
  dq_score: number;
  readiness_score: number;
  schema_signed: boolean;
  temporal_issue_count: number;
  needs_vocab_remap: boolean;
  notes: string;
};

type PatientFormState = {
  site_name: string;
  country: string;
  operator_id: string;
  patient_pseudonym: string;
  sex: string;
  year_of_birth: string;
  diagnosis_date: string;
  chronic_hbv_confirmed: boolean;
  on_na_therapy: boolean;
  bepirovirsen_eligible: boolean;
  started_bepirovirsen: boolean;
  baseline_hbsag: string;
  baseline_hbv_dna: string;
  baseline_alt: string;
  baseline_ast: string;
  hbeag_status: string;
  bilirubin: string;
  albumin: string;
  inr: string;
  notes: string;
};

type VisitFormState = {
  patient_id: string;
  visit_date: string;
  visit_type: string;
  quantitative_hbsag: string;
  hbv_dna: string;
  hbv_dna_detectable: boolean;
  alt: string;
  ast: string;
  hbeag_status: string;
  bilirubin: string;
  albumin: string;
  inr: string;
  on_na_therapy: boolean;
  on_bepirovirsen: boolean;
  functional_cure_endpoint: boolean;
  notes: string;
};

type PermitFormState = {
  permit_id: string;
  requesting_organization: string;
  purpose_code: string;
  expiry_date: string;
  issuing_hdab: string;
  notes: string;
};

type FlatVisit = Visit & {
  patient_pseudonym: string;
};

const initialDatasetForm: DatasetFormState = {
  site_name: '',
  source_type: 'EHR',
  country: 'DE',
  operator_id: '',
  record_count: 100,
  hbv_cohort: 100,
  bepirovirsen_treated: 0,
  dq_score: 90,
  readiness_score: 85,
  schema_signed: true,
  temporal_issue_count: 0,
  needs_vocab_remap: false,
  notes: '',
};

const initialPatientForm: PatientFormState = {
  site_name: '',
  country: 'DE',
  operator_id: '',
  patient_pseudonym: '',
  sex: 'unknown',
  year_of_birth: '1980',
  diagnosis_date: '',
  chronic_hbv_confirmed: true,
  on_na_therapy: false,
  bepirovirsen_eligible: false,
  started_bepirovirsen: false,
  baseline_hbsag: '',
  baseline_hbv_dna: '',
  baseline_alt: '',
  baseline_ast: '',
  hbeag_status: 'unknown',
  bilirubin: '',
  albumin: '',
  inr: '',
  notes: '',
};

const initialVisitForm: VisitFormState = {
  patient_id: '',
  visit_date: '',
  visit_type: 'baseline',
  quantitative_hbsag: '',
  hbv_dna: '',
  hbv_dna_detectable: true,
  alt: '',
  ast: '',
  hbeag_status: 'unknown',
  bilirubin: '',
  albumin: '',
  inr: '',
  on_na_therapy: false,
  on_bepirovirsen: false,
  functional_cure_endpoint: false,
  notes: '',
};

const initialPermitForm: PermitFormState = {
  permit_id: '',
  requesting_organization: '',
  purpose_code: 'research',
  expiry_date: '',
  issuing_hdab: 'Simulated HDAB',
  notes: '',
};

const fallbackData: DashboardPayload = {
  prototype: {
    name: 'RWD TrustChain',
    subtitle:
      'Interactive prototype for secure dataset intake, patient/visit capture, validation, and simulated ledger notarization.',
    challenge: [],
    regulatory_alignment: [],
  },
  top_cards: [],
  source_feeds: [],
  omop_etl: {
    current_snapshot: {
      snapshot_id: '',
      snapshot_status: 'warning',
      mapping_coverage: 0,
      vocabulary_coverage: 0,
      quality_gate_pass_rate: 0,
      snapshot_block: null,
    },
    run_context: {
      run_id: '',
      etl_spec_version: '',
      vocabulary_release: '',
      target_cdm: '',
      last_run_at: '',
      status: 'warning',
    },
    domain_loads: [],
    mapping_gaps: [],
  },
  permit_gate: {
    restricted: true,
    banner: 'No active permit',
    active_permit: null,
  },
  data_lifecycle: [],
  ledger: [],
  quality: {
    dimensions: [],
    issue_severity: [],
    readiness_trend: [],
    source_coverage: [],
    open_findings: [],
  },
  trial_readiness: [],
  next_steps: [],
};

function appendIfPresent(formData: FormData, key: string, value: string) {
  if (value.trim() !== '') {
    formData.append(key, value);
  }
}

function formatNullable(value: number | null) {
  return value === null ? '—' : String(value);
}

function FormSection({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="clinical-section">
      <div className="clinical-section-header">
        <div>
          <h3>{title}</h3>
          <p className="section-copy">{description}</p>
        </div>
      </div>
      <div className="form-grid">{children}</div>
    </section>
  );
}

function App() {
  const [data, setData] = useState<DashboardPayload>(fallbackData);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [permits, setPermits] = useState<PermitRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingDataset, setSavingDataset] = useState(false);
  const [savingPatient, setSavingPatient] = useState(false);
  const [savingVisit, setSavingVisit] = useState(false);
  const [savingPermit, setSavingPermit] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [verificationNotice, setVerificationNotice] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [datasetForm, setDatasetForm] = useState<DatasetFormState>(initialDatasetForm);
  const [patientForm, setPatientForm] = useState<PatientFormState>(initialPatientForm);
  const [visitForm, setVisitForm] = useState<VisitFormState>(initialVisitForm);
  const [permitForm, setPermitForm] = useState<PermitFormState>(initialPermitForm);

  const loadAll = async () => {
    const dashboardResponse = await fetch(`${API_BASE}/prototype/dashboard`);
    if (!dashboardResponse.ok) {
      throw new Error(`Dashboard request failed with status ${dashboardResponse.status}`);
    }
    const dashboardPayload = (await dashboardResponse.json()) as DashboardPayload;
    setData(dashboardPayload);

    const permitsResponse = await fetch(`${API_BASE}/prototype/permits`);
    if (!permitsResponse.ok) {
      throw new Error(`Permits request failed with status ${permitsResponse.status}`);
    }
    const permitsPayload = (await permitsResponse.json()) as {
      items: PermitRecord[];
      active_permit: PermitRecord | null;
    };
    setPermits(permitsPayload.items);

    if (dashboardPayload.permit_gate.restricted) {
      setSubmissions([]);
      setPatients([]);
      return;
    }

    const submissionsResponse = await fetch(`${API_BASE}/prototype/submissions`);
    if (!submissionsResponse.ok) {
      throw new Error(`Submissions request failed with status ${submissionsResponse.status}`);
    }
    const submissionsPayload = (await submissionsResponse.json()) as { items: Submission[] };
    setSubmissions(submissionsPayload.items);

    const patientsResponse = await fetch(`${API_BASE}/prototype/patients`);
    if (!patientsResponse.ok) {
      throw new Error(`Patients request failed with status ${patientsResponse.status}`);
    }
    const patientsPayload = (await patientsResponse.json()) as { items: Patient[] };
    setPatients(patientsPayload.items);
  };

  useEffect(() => {
    const run = async () => {
      try {
        await loadAll();
      } catch {
        setError('The frontend could not load the interactive prototype API.');
      } finally {
        setLoading(false);
      }
    };

    void run();
  }, []);

  useEffect(() => {
    if (!visitForm.patient_id && patients.length > 0) {
      setVisitForm((prev) => ({ ...prev, patient_id: patients[0].id }));
    }
  }, [patients, visitForm.patient_id]);

  const sortedLedger = useMemo(
    () => [...data.ledger].sort((a, b) => b.block - a.block),
    [data.ledger]
  );

  const allVisits = useMemo<FlatVisit[]>(
    () =>
      patients
        .flatMap((patient) =>
          patient.visits.map((visit) => ({
            ...visit,
            patient_pseudonym: patient.patient_pseudonym,
          }))
        )
        .sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [patients]
  );

  const handleDatasetChange = (
    event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const target = event.target;
    const { name, value } = target;

    if (target instanceof HTMLInputElement && target.type === 'checkbox') {
      setDatasetForm((prev) => ({ ...prev, [name]: target.checked }));
      return;
    }

    const numericFields = new Set([
      'record_count',
      'hbv_cohort',
      'bepirovirsen_treated',
      'dq_score',
      'readiness_score',
      'temporal_issue_count',
    ]);

    setDatasetForm((prev) => ({
      ...prev,
      [name]: numericFields.has(name) ? Number(value) : value,
    }));
  };

  const handlePatientChange = (
    event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const target = event.target;
    const { name, value } = target;

    if (target instanceof HTMLInputElement && target.type === 'checkbox') {
      setPatientForm((prev) => ({ ...prev, [name]: target.checked }));
      return;
    }

    setPatientForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleVisitChange = (
    event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const target = event.target;
    const { name, value } = target;

    if (target instanceof HTMLInputElement && target.type === 'checkbox') {
      setVisitForm((prev) => ({ ...prev, [name]: target.checked }));
      return;
    }

    setVisitForm((prev) => ({ ...prev, [name]: value }));
  };

  const handlePermitChange = (
    event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = event.target;
    setPermitForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleDatasetSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSavingDataset(true);
    setNotice('');
    setVerificationNotice('');

    try {
      const payload = new FormData();
      Object.entries(datasetForm).forEach(([key, value]) => {
        payload.append(key, String(value));
      });

      if (selectedFile) {
        payload.append('file', selectedFile);
      }

      const response = await fetch(`${API_BASE}/prototype/submissions`, {
        method: 'POST',
        body: payload,
      });

      if (!response.ok) {
        throw new Error(`Submission failed with status ${response.status}`);
      }

      const result = (await response.json()) as { ledger_entry: LedgerEntry };
      await loadAll();
      setNotice(`Dataset stored. Simulated block ${result.ledger_entry.block} created.`);
      setDatasetForm(initialDatasetForm);
      setSelectedFile(null);
    } catch {
      setNotice('The dataset submission could not be stored. Check that the backend is running.');
    } finally {
      setSavingDataset(false);
    }
  };

  const handlePatientSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSavingPatient(true);
    setNotice('');
    setVerificationNotice('');

    try {
      const payload = new FormData();
      payload.append('site_name', patientForm.site_name);
      payload.append('country', patientForm.country);
      payload.append('operator_id', patientForm.operator_id);
      payload.append('patient_pseudonym', patientForm.patient_pseudonym);
      payload.append('sex', patientForm.sex);
      payload.append('year_of_birth', patientForm.year_of_birth);
      payload.append('diagnosis_date', patientForm.diagnosis_date);
      payload.append('chronic_hbv_confirmed', String(patientForm.chronic_hbv_confirmed));
      payload.append('on_na_therapy', String(patientForm.on_na_therapy));
      payload.append('bepirovirsen_eligible', String(patientForm.bepirovirsen_eligible));
      payload.append('started_bepirovirsen', String(patientForm.started_bepirovirsen));
      appendIfPresent(payload, 'baseline_hbsag', patientForm.baseline_hbsag);
      appendIfPresent(payload, 'baseline_hbv_dna', patientForm.baseline_hbv_dna);
      appendIfPresent(payload, 'baseline_alt', patientForm.baseline_alt);
      appendIfPresent(payload, 'baseline_ast', patientForm.baseline_ast);
      payload.append('hbeag_status', patientForm.hbeag_status);
      appendIfPresent(payload, 'bilirubin', patientForm.bilirubin);
      appendIfPresent(payload, 'albumin', patientForm.albumin);
      appendIfPresent(payload, 'inr', patientForm.inr);
      payload.append('notes', patientForm.notes);

      const response = await fetch(`${API_BASE}/prototype/patients`, {
        method: 'POST',
        body: payload,
      });

      if (!response.ok) {
        throw new Error(`Patient create failed with status ${response.status}`);
      }

      const result = (await response.json()) as { patient: Patient; ledger_entry: LedgerEntry };
      await loadAll();
      setNotice(`Patient baseline stored. Simulated block ${result.ledger_entry.block} created.`);
      setPatientForm(initialPatientForm);
      setVisitForm((prev) => ({
        ...prev,
        patient_id: result.patient.id,
      }));
    } catch {
      setNotice('The patient baseline record could not be stored.');
    } finally {
      setSavingPatient(false);
    }
  };

  const handleVisitSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!visitForm.patient_id) {
      setNotice('Choose a patient before submitting a visit.');
      return;
    }

    setSavingVisit(true);
    setNotice('');
    setVerificationNotice('');

    try {
      const payload = new FormData();
      payload.append('visit_date', visitForm.visit_date);
      payload.append('visit_type', visitForm.visit_type);
      appendIfPresent(payload, 'quantitative_hbsag', visitForm.quantitative_hbsag);
      appendIfPresent(payload, 'hbv_dna', visitForm.hbv_dna);
      payload.append('hbv_dna_detectable', String(visitForm.hbv_dna_detectable));
      appendIfPresent(payload, 'alt', visitForm.alt);
      appendIfPresent(payload, 'ast', visitForm.ast);
      payload.append('hbeag_status', visitForm.hbeag_status);
      appendIfPresent(payload, 'bilirubin', visitForm.bilirubin);
      appendIfPresent(payload, 'albumin', visitForm.albumin);
      appendIfPresent(payload, 'inr', visitForm.inr);
      payload.append('on_na_therapy', String(visitForm.on_na_therapy));
      payload.append('on_bepirovirsen', String(visitForm.on_bepirovirsen));
      payload.append('functional_cure_endpoint', String(visitForm.functional_cure_endpoint));
      payload.append('notes', visitForm.notes);

      const response = await fetch(`${API_BASE}/prototype/patients/${visitForm.patient_id}/visits`, {
        method: 'POST',
        body: payload,
      });

      if (!response.ok) {
        throw new Error(`Visit create failed with status ${response.status}`);
      }

      const result = (await response.json()) as { ledger_entry: LedgerEntry };
      await loadAll();
      setNotice(`Visit stored. Simulated block ${result.ledger_entry.block} created.`);
      setVisitForm((prev) => ({
        ...initialVisitForm,
        patient_id: prev.patient_id,
      }));
    } catch {
      setNotice('The visit record could not be stored.');
    } finally {
      setSavingVisit(false);
    }
  };

  const handlePermitSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSavingPermit(true);
    setNotice('');
    setVerificationNotice('');

    try {
      const payload = new FormData();
      payload.append('permit_id', permitForm.permit_id);
      payload.append('requesting_organization', permitForm.requesting_organization);
      payload.append('purpose_code', permitForm.purpose_code);
      payload.append('expiry_date', permitForm.expiry_date);
      payload.append('issuing_hdab', permitForm.issuing_hdab);
      payload.append('notes', permitForm.notes);

      const response = await fetch(`${API_BASE}/prototype/permits`, {
        method: 'POST',
        body: payload,
      });

      if (!response.ok) {
        throw new Error(`Permit create failed with status ${response.status}`);
      }

      await loadAll();
      setNotice(`Permit ${permitForm.permit_id} stored and activated.`);
      setPermitForm(initialPermitForm);
    } catch {
      setNotice('The data access permit could not be stored.');
    } finally {
      setSavingPermit(false);
    }
  };

  const verifyEndpoint = async (url: string, label: string) => {
    setVerificationNotice('');
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Verify failed with status ${response.status}`);
      }
      const result = (await response.json()) as VerifyResponse;
      setVerificationNotice(
        result.verified
          ? `${label} verified successfully in block ${result.ledger_block}.`
          : `${label} failed verification.}`
      );
    } catch {
      setVerificationNotice('Verification request failed.');
    }
  };

  return (
    <div className="page-shell">
      <header className="hero-card">
        <div>
          <span className="eyebrow">Interactive GSK challenge prototype</span>
          <h1>{data.prototype.name}</h1>
          <p className="hero-copy">{data.prototype.subtitle}</p>
          <p className="mini-note">
            This version supports dataset submissions, structured HBV patient baseline entry,
            longitudinal visit capture, SHA-256 artifact hashing, simulated ledger blocks, OMOP /
            ETL reporting, and EHDS-style permit-gated secondary-use access.
          </p>
        </div>
        <div className="badge-row">
          {data.prototype.regulatory_alignment.map((badge) => (
            <span key={badge} className="badge">
              {badge}
            </span>
          ))}
        </div>
      </header>

      {error ? <div className="notice warning">{error}</div> : null}
      {notice ? <div className="notice success">{notice}</div> : null}
      {verificationNotice ? <div className="notice">{verificationNotice}</div> : null}
      {loading ? <div className="notice">Loading prototype dashboard...</div> : null}

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Data access permit</h2>
            <p className="section-copy">
              Secondary-use dashboard access is controlled by a simulated EHDS-style data access
              permit.
            </p>
          </div>
        </div>

        <div className="two-column">
          <div className="panel">
            <div className="section-header compact">
              <div>
                <h2>Permit gate status</h2>
                <p className="section-copy">
                  All downstream analytics, patient data, ledger detail, and dashboard views
                  operate under the active permit.
                </p>
              </div>
            </div>

            <div
              className={`permit-banner ${
                data.permit_gate.restricted ? 'restricted' : 'active'
              }`}
            >
              <strong>{data.permit_gate.banner}</strong>
            </div>

            {data.permit_gate.active_permit ? (
              <div className="omop-meta">
                <div className="feed-meta-row">
                  <span>Permit ID</span>
                  <strong>{data.permit_gate.active_permit.permit_id}</strong>
                </div>
                <div className="feed-meta-row">
                  <span>Requesting organisation</span>
                  <strong>{data.permit_gate.active_permit.requesting_organization}</strong>
                </div>
                <div className="feed-meta-row">
                  <span>Purpose code</span>
                  <strong>{data.permit_gate.active_permit.purpose_code}</strong>
                </div>
                <div className="feed-meta-row">
                  <span>Expiry date</span>
                  <strong>{data.permit_gate.active_permit.expiry_date}</strong>
                </div>
                <div className="feed-meta-row">
                  <span>Issuing HDAB</span>
                  <strong>{data.permit_gate.active_permit.issuing_hdab}</strong>
                </div>
              </div>
            ) : null}

            <div className="omop-gap-block">
              <h3>Recent permits</h3>
              <ul className="finding-list">
                {permits.length > 0 ? (
                  permits.slice(0, 3).map((permit) => (
                    <li key={permit.id}>
                      {permit.permit_id} · {permit.requesting_organization} · {permit.status}
                    </li>
                  ))
                ) : (
                  <li>No permits registered yet.</li>
                )}
              </ul>
            </div>
          </div>

          <div className="panel">
            <div className="section-header compact">
              <div>
                <h2>Register permit</h2>
                <p className="section-copy">
                  Create a simulated secondary-use data access permit to unlock the dashboard.
                </p>
              </div>
            </div>

            <form onSubmit={handlePermitSubmit}>
              <div className="form-grid">
                <label className="field">
                  <span>Permit ID</span>
                  <input
                    name="permit_id"
                    value={permitForm.permit_id}
                    onChange={handlePermitChange}
                    placeholder="e.g. EHDS-2026-001"
                    required
                  />
                </label>

                <label className="field">
                  <span>Requesting organisation</span>
                  <input
                    name="requesting_organization"
                    value={permitForm.requesting_organization}
                    onChange={handlePermitChange}
                    placeholder="e.g. GSK RWE Team"
                    required
                  />
                </label>

                <label className="field">
                  <span>Purpose code</span>
                  <select
                    name="purpose_code"
                    value={permitForm.purpose_code}
                    onChange={handlePermitChange}
                  >
                    <option value="research">research</option>
                    <option value="innovation">innovation</option>
                    <option value="policy_making">policy_making</option>
                    <option value="patient_safety">patient_safety</option>
                    <option value="personalized_medicine">personalized_medicine</option>
                    <option value="official_statistics">official_statistics</option>
                    <option value="regulatory">regulatory</option>
                    <option value="health_threat_preparedness">health_threat_preparedness</option>
                  </select>
                </label>

                <label className="field">
                  <span>Expiry date</span>
                  <input
                    type="date"
                    name="expiry_date"
                    value={permitForm.expiry_date}
                    onChange={handlePermitChange}
                    required
                  />
                </label>

                <label className="field">
                  <span>Issuing HDAB</span>
                  <input
                    name="issuing_hdab"
                    value={permitForm.issuing_hdab}
                    onChange={handlePermitChange}
                    required
                  />
                </label>

                <label className="field field-full">
                  <span>Notes</span>
                  <textarea
                    name="notes"
                    value={permitForm.notes}
                    onChange={handlePermitChange}
                    rows={3}
                    placeholder="Scope restrictions, data minimisation notes, export restrictions, or governance comments."
                  />
                </label>
              </div>

              <div className="action-row">
                <button type="submit" disabled={savingPermit}>
                  {savingPermit ? 'Saving...' : 'Store permit'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </section>

      {data.permit_gate.restricted ? (
        <section className="section">
          <div className="panel restricted-panel">
            <h2>Dashboard restricted</h2>
            <p className="section-copy">
              Secondary-use analytics, patient registry views, provenance detail, and ETL dashboards
              are locked until an active data access permit is registered.
            </p>
          </div>
        </section>
      ) : null}

      {!data.permit_gate.restricted ? (
        <>
          <section className="section">
            <div className="section-header">
              <div>
                <h2>Dataset submission</h2>
                <p className="section-copy">
                  Simulate a site dataset drop. The backend stores the metadata, hashes the payload,
                  and appends a simulated ledger block.
                </p>
              </div>
            </div>

            <form className="panel" onSubmit={handleDatasetSubmit}>
              <div className="form-grid">
                <label className="field">
                  <span>Site name</span>
                  <input
                    name="site_name"
                    value={datasetForm.site_name}
                    onChange={handleDatasetChange}
                    required
                  />
                </label>

                <label className="field">
                  <span>Source type</span>
                  <select
                    name="source_type"
                    value={datasetForm.source_type}
                    onChange={handleDatasetChange}
                  >
                    <option value="EHR">EHR</option>
                    <option value="Laboratory">Laboratory</option>
                    <option value="Imaging">Imaging</option>
                    <option value="Pharmacy">Pharmacy</option>
                    <option value="Claims">Claims</option>
                    <option value="Wearable">Wearable</option>
                  </select>
                </label>

                <label className="field">
                  <span>Country</span>
                  <input
                    name="country"
                    value={datasetForm.country}
                    onChange={handleDatasetChange}
                    required
                  />
                </label>

                <label className="field">
                  <span>Operator ID</span>
                  <input
                    name="operator_id"
                    value={datasetForm.operator_id}
                    onChange={handleDatasetChange}
                    required
                  />
                </label>

                <label className="field">
                  <span>Record count</span>
                  <input
                    type="number"
                    min="0"
                    name="record_count"
                    value={datasetForm.record_count}
                    onChange={handleDatasetChange}
                    required
                  />
                </label>

                <label className="field">
                  <span>HBV cohort represented</span>
                  <input
                    type="number"
                    min="0"
                    name="hbv_cohort"
                    value={datasetForm.hbv_cohort}
                    onChange={handleDatasetChange}
                    required
                  />
                </label>

                <label className="field">
                  <span>Bepirovirsen-treated</span>
                  <input
                    type="number"
                    min="0"
                    name="bepirovirsen_treated"
                    value={datasetForm.bepirovirsen_treated}
                    onChange={handleDatasetChange}
                    required
                  />
                </label>

                <label className="field">
                  <span>Data quality score</span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    name="dq_score"
                    value={datasetForm.dq_score}
                    onChange={handleDatasetChange}
                    required
                  />
                </label>

                <label className="field">
                  <span>Readiness score</span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    name="readiness_score"
                    value={datasetForm.readiness_score}
                    onChange={handleDatasetChange}
                    required
                  />
                </label>

                <label className="field">
                  <span>Temporal issue count</span>
                  <input
                    type="number"
                    min="0"
                    name="temporal_issue_count"
                    value={datasetForm.temporal_issue_count}
                    onChange={handleDatasetChange}
                    required
                  />
                </label>

                <label className="field field-checkbox">
                  <span>Schema manifest signed</span>
                  <input
                    type="checkbox"
                    name="schema_signed"
                    checked={datasetForm.schema_signed}
                    onChange={handleDatasetChange}
                  />
                </label>

                <label className="field field-checkbox">
                  <span>Needs OMOP vocabulary remap</span>
                  <input
                    type="checkbox"
                    name="needs_vocab_remap"
                    checked={datasetForm.needs_vocab_remap}
                    onChange={handleDatasetChange}
                  />
                </label>

                <label className="field field-full">
                  <span>Notes</span>
                  <textarea
                    name="notes"
                    value={datasetForm.notes}
                    onChange={handleDatasetChange}
                    rows={3}
                  />
                </label>

                <label className="field field-full">
                  <span>Optional file upload</span>
                  <input
                    type="file"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
                  />
                  <small>Only the file hash is incorporated into the artifact fingerprint.</small>
                </label>
              </div>

              <div className="action-row">
                <button type="submit" disabled={savingDataset}>
                  {savingDataset ? 'Submitting...' : 'Submit dataset'}
                </button>
              </div>
            </form>
          </section>

          <section className="section">
            <div className="section-header">
              <div>
                <h2>Clinical HBV patient pathway</h2>
                <p className="section-copy">
                  The patient workflow is now organized into screening, baseline, treatment,
                  on-treatment, and post-treatment sections to feel closer to a real clinical
                  capture flow.
                </p>
              </div>
            </div>

            <div className="care-pathway">
              <div className="pathway-step active">
                <span>1</span>
                <strong>Screening</strong>
                <small>Identify and confirm CHB</small>
              </div>
              <div className="pathway-step active">
                <span>2</span>
                <strong>Baseline</strong>
                <small>Capture HBV markers and liver function</small>
              </div>
              <div className="pathway-step active">
                <span>3</span>
                <strong>Treatment status</strong>
                <small>NA therapy and bepirovirsen pathway</small>
              </div>
              <div className="pathway-step active">
                <span>4</span>
                <strong>On-treatment visits</strong>
                <small>Serial HBsAg, HBV DNA, ALT, AST</small>
              </div>
              <div className="pathway-step active">
                <span>5</span>
                <strong>Post-treatment</strong>
                <small>Functional cure endpoint tracking</small>
              </div>
            </div>
          </section>

          <section className="section two-column">
            <div className="panel clinical-panel">
              <div className="section-header compact">
                <div>
                  <h2>Register HBV patient baseline</h2>
                  <p className="section-copy">
                    Create a pseudonymised baseline patient record with screening history, baseline
                    virology, liver markers, and treatment status.
                  </p>
                </div>
              </div>

              <form onSubmit={handlePatientSubmit}>
                <FormSection
                  title="Screening and identification"
                  description="Capture the site, patient pseudonym, demographics, and confirmation of chronic HBV."
                >
                  <label className="field">
                    <span>Site name</span>
                    <input
                      name="site_name"
                      value={patientForm.site_name}
                      onChange={handlePatientChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span>Country</span>
                    <input
                      name="country"
                      value={patientForm.country}
                      onChange={handlePatientChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span>Operator ID</span>
                    <input
                      name="operator_id"
                      value={patientForm.operator_id}
                      onChange={handlePatientChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span>Patient pseudonym</span>
                    <input
                      name="patient_pseudonym"
                      value={patientForm.patient_pseudonym}
                      onChange={handlePatientChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span>Sex</span>
                    <select name="sex" value={patientForm.sex} onChange={handlePatientChange}>
                      <option value="unknown">Unknown</option>
                      <option value="female">Female</option>
                      <option value="male">Male</option>
                      <option value="other">Other</option>
                    </select>
                  </label>

                  <label className="field">
                    <span>Year of birth</span>
                    <input
                      type="number"
                      name="year_of_birth"
                      value={patientForm.year_of_birth}
                      onChange={handlePatientChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span>Diagnosis date</span>
                    <input
                      type="date"
                      name="diagnosis_date"
                      value={patientForm.diagnosis_date}
                      onChange={handlePatientChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span>HBeAg status at baseline</span>
                    <select
                      name="hbeag_status"
                      value={patientForm.hbeag_status}
                      onChange={handlePatientChange}
                    >
                      <option value="unknown">Unknown</option>
                      <option value="positive">Positive</option>
                      <option value="negative">Negative</option>
                    </select>
                  </label>

                  <label className="field field-checkbox">
                    <span>Chronic HBV confirmed</span>
                    <input
                      type="checkbox"
                      name="chronic_hbv_confirmed"
                      checked={patientForm.chronic_hbv_confirmed}
                      onChange={handlePatientChange}
                    />
                  </label>
                </FormSection>

                <FormSection
                  title="Baseline virology and liver function"
                  description="Capture the variables most relevant to HBV disease activity and bepirovirsen response monitoring."
                >
                  <label className="field">
                    <span>Baseline HBsAg</span>
                    <input
                      name="baseline_hbsag"
                      value={patientForm.baseline_hbsag}
                      onChange={handlePatientChange}
                      placeholder="e.g. 3.4"
                    />
                  </label>

                  <label className="field">
                    <span>Baseline HBV DNA</span>
                    <input
                      name="baseline_hbv_dna"
                      value={patientForm.baseline_hbv_dna}
                      onChange={handlePatientChange}
                      placeholder="e.g. 1250"
                    />
                  </label>

                  <label className="field">
                    <span>Baseline ALT</span>
                    <input
                      name="baseline_alt"
                      value={patientForm.baseline_alt}
                      onChange={handlePatientChange}
                      placeholder="e.g. 42"
                    />
                  </label>

                  <label className="field">
                    <span>Baseline AST</span>
                    <input
                      name="baseline_ast"
                      value={patientForm.baseline_ast}
                      onChange={handlePatientChange}
                      placeholder="e.g. 38"
                    />
                  </label>

                  <label className="field">
                    <span>Bilirubin</span>
                    <input
                      name="bilirubin"
                      value={patientForm.bilirubin}
                      onChange={handlePatientChange}
                    />
                  </label>

                  <label className="field">
                    <span>Albumin</span>
                    <input
                      name="albumin"
                      value={patientForm.albumin}
                      onChange={handlePatientChange}
                    />
                  </label>

                  <label className="field">
                    <span>INR</span>
                    <input name="inr" value={patientForm.inr} onChange={handlePatientChange} />
                  </label>
                </FormSection>

                <FormSection
                  title="Treatment pathway"
                  description="Record pre-existing NA therapy and whether the patient is eligible for or has started bepirovirsen."
                >
                  <label className="field field-checkbox">
                    <span>On NA therapy</span>
                    <input
                      type="checkbox"
                      name="on_na_therapy"
                      checked={patientForm.on_na_therapy}
                      onChange={handlePatientChange}
                    />
                  </label>

                  <label className="field field-checkbox">
                    <span>Bepirovirsen eligible</span>
                    <input
                      type="checkbox"
                      name="bepirovirsen_eligible"
                      checked={patientForm.bepirovirsen_eligible}
                      onChange={handlePatientChange}
                    />
                  </label>

                  <label className="field field-checkbox">
                    <span>Started bepirovirsen</span>
                    <input
                      type="checkbox"
                      name="started_bepirovirsen"
                      checked={patientForm.started_bepirovirsen}
                      onChange={handlePatientChange}
                    />
                  </label>

                  <label className="field field-full">
                    <span>Clinical notes</span>
                    <textarea
                      name="notes"
                      value={patientForm.notes}
                      onChange={handlePatientChange}
                      rows={3}
                      placeholder="Eligibility rationale, family history, symptoms, alcohol use, comorbidities, or other clinical context."
                    />
                  </label>
                </FormSection>

                <div className="action-row">
                  <button type="submit" disabled={savingPatient}>
                    {savingPatient ? 'Saving...' : 'Save patient baseline'}
                  </button>
                </div>
              </form>
            </div>

            <div className="panel clinical-panel">
              <div className="section-header compact">
                <div>
                  <h2>Add longitudinal visit</h2>
                  <p className="section-copy">
                    Record on-treatment or post-treatment monitoring visits with serial HBV markers
                    and outcome state.
                  </p>
                </div>
              </div>

              <form onSubmit={handleVisitSubmit}>
                <FormSection
                  title="Visit context"
                  description="Choose the patient and define where the visit sits in the pathway."
                >
                  <label className="field field-full">
                    <span>Patient</span>
                    <select
                      name="patient_id"
                      value={visitForm.patient_id}
                      onChange={handleVisitChange}
                      required
                    >
                      <option value="">Select patient</option>
                      {patients.map((patient) => (
                        <option key={patient.id} value={patient.id}>
                          {patient.patient_pseudonym} · {patient.site_name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="field">
                    <span>Visit date</span>
                    <input
                      type="date"
                      name="visit_date"
                      value={visitForm.visit_date}
                      onChange={handleVisitChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span>Visit stage</span>
                    <select
                      name="visit_type"
                      value={visitForm.visit_type}
                      onChange={handleVisitChange}
                    >
                      <option value="screening">Screening</option>
                      <option value="baseline">Baseline</option>
                      <option value="on-treatment">On-treatment</option>
                      <option value="follow-up">Follow-up</option>
                      <option value="post-treatment">Post-treatment</option>
                    </select>
                  </label>
                </FormSection>

                <FormSection
                  title="On-treatment virology and inflammation"
                  description="Capture the core longitudinal markers for response monitoring."
                >
                  <label className="field">
                    <span>Quantitative HBsAg</span>
                    <input
                      name="quantitative_hbsag"
                      value={visitForm.quantitative_hbsag}
                      onChange={handleVisitChange}
                    />
                  </label>

                  <label className="field">
                    <span>HBV DNA</span>
                    <input name="hbv_dna" value={visitForm.hbv_dna} onChange={handleVisitChange} />
                  </label>

                  <label className="field">
                    <span>ALT</span>
                    <input name="alt" value={visitForm.alt} onChange={handleVisitChange} />
                  </label>

                  <label className="field">
                    <span>AST</span>
                    <input name="ast" value={visitForm.ast} onChange={handleVisitChange} />
                  </label>

                  <label className="field">
                    <span>HBeAg status</span>
                    <select
                      name="hbeag_status"
                      value={visitForm.hbeag_status}
                      onChange={handleVisitChange}
                    >
                      <option value="unknown">Unknown</option>
                      <option value="positive">Positive</option>
                      <option value="negative">Negative</option>
                    </select>
                  </label>

                  <label className="field field-checkbox">
                    <span>HBV DNA detectable</span>
                    <input
                      type="checkbox"
                      name="hbv_dna_detectable"
                      checked={visitForm.hbv_dna_detectable}
                      onChange={handleVisitChange}
                    />
                  </label>
                </FormSection>

                <FormSection
                  title="Safety and liver function"
                  description="Capture additional liver function markers used for monitoring and interpretation."
                >
                  <label className="field">
                    <span>Bilirubin</span>
                    <input
                      name="bilirubin"
                      value={visitForm.bilirubin}
                      onChange={handleVisitChange}
                    />
                  </label>

                  <label className="field">
                    <span>Albumin</span>
                    <input
                      name="albumin"
                      value={visitForm.albumin}
                      onChange={handleVisitChange}
                    />
                  </label>

                  <label className="field">
                    <span>INR</span>
                    <input name="inr" value={visitForm.inr} onChange={handleVisitChange} />
                  </label>
                </FormSection>

                <FormSection
                  title="Treatment and post-treatment outcome"
                  description="Track current therapy state and whether the patient has reached the functional cure endpoint."
                >
                  <label className="field field-checkbox">
                    <span>On NA therapy</span>
                    <input
                      type="checkbox"
                      name="on_na_therapy"
                      checked={visitForm.on_na_therapy}
                      onChange={handleVisitChange}
                    />
                  </label>

                  <label className="field field-checkbox">
                    <span>On bepirovirsen</span>
                    <input
                      type="checkbox"
                      name="on_bepirovirsen"
                      checked={visitForm.on_bepirovirsen}
                      onChange={handleVisitChange}
                    />
                  </label>

                  <label className="field field-checkbox">
                    <span>Functional cure endpoint</span>
                    <input
                      type="checkbox"
                      name="functional_cure_endpoint"
                      checked={visitForm.functional_cure_endpoint}
                      onChange={handleVisitChange}
                    />
                  </label>

                  <label className="field field-full">
                    <span>Visit notes</span>
                    <textarea
                      name="notes"
                      value={visitForm.notes}
                      onChange={handleVisitChange}
                      rows={3}
                      placeholder="Clinical interpretation, flare comments, adherence notes, or follow-up plan."
                    />
                  </label>
                </FormSection>

                <div className="action-row">
                  <button type="submit" disabled={savingVisit || patients.length === 0}>
                    {savingVisit ? 'Saving...' : 'Save visit'}
                  </button>
                </div>
              </form>
            </div>
          </section>

          <section className="section">
            <div className="section-header">
              <div>
                <h2>Challenge focus</h2>
                <p className="section-copy">
                  The prototype now demonstrates both dataset intake and structured HBV patient
                  pathway capture.
                </p>
              </div>
            </div>
            <div className="challenge-grid">
              {data.prototype.challenge.map((item) => (
                <article key={item} className="challenge-card">
                  <span className="challenge-number">•</span>
                  <p>{item}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="section">
            <div className="section-header">
              <div>
                <h2>Live prototype KPIs</h2>
                <p className="section-copy">
                  These cards update when you submit datasets, register patients, or add visits.
                </p>
              </div>
            </div>
            <div className="kpi-grid">
              {data.top_cards.map((card) => (
                <article key={card.label} className="kpi-card">
                  <div className="kpi-label">{card.label}</div>
                  <div className="kpi-value">{card.value}</div>
                  <div className="kpi-note">{card.note}</div>
                </article>
              ))}
            </div>
          </section>

          <section className="section">
            <div className="section-header">
              <div>
                <h2>Source intake by feed</h2>
                <p className="section-copy">
                  Each upstream feed is shown separately so you can monitor ingest status, schema
                  quality, integrity, and linkage readiness across EHR, lab, imaging, pharmacy,
                  claims, and wearable data.
                </p>
              </div>
            </div>

            <div className="feed-grid">
              {data.source_feeds.map((feed) => {
                const statusLabel =
                  feed.feed_status === 'healthy'
                    ? 'Healthy'
                    : feed.feed_status === 'warning'
                    ? 'Attention'
                    : 'Pending';

                const statusClass =
                  feed.feed_status === 'healthy'
                    ? 'verified'
                    : feed.feed_status === 'warning'
                    ? 'monitor'
                    : 'pending-chip';

                return (
                  <article key={feed.source} className={`feed-card ${feed.feed_status}`}>
                    <div className="feed-topline">
                      <h3>{feed.source}</h3>
                      <span className={`status-chip ${statusClass}`}>{statusLabel}</span>
                    </div>

                    <p className="feed-note">{feed.note}</p>

                    <div className="feed-stats">
                      <div className="feed-metric">
                        <span>Records</span>
                        <strong>{feed.records}</strong>
                      </div>
                      <div className="feed-metric">
                        <span>Sites</span>
                        <strong>{feed.sites}</strong>
                      </div>
                      <div className="feed-metric">
                        <span>Avg DQ</span>
                        <strong>{feed.avg_dq > 0 ? feed.avg_dq.toFixed(1) : '—'}</strong>
                      </div>
                      <div className="feed-metric">
                        <span>Countries</span>
                        <strong>{feed.countries}</strong>
                      </div>
                    </div>

                    <div className="feed-meta">
                      <div className="feed-meta-row">
                        <span>Last ingest</span>
                        <strong>{feed.last_ingest}</strong>
                      </div>
                      <div className="feed-meta-row">
                        <span>Schema</span>
                        <strong>{feed.schema_status}</strong>
                      </div>
                      <div className="feed-meta-row">
                        <span>Integrity</span>
                        <strong>{feed.integrity_status}</strong>
                      </div>
                      <div className="feed-meta-row">
                        <span>Linkage</span>
                        <strong>{feed.linkage_status}</strong>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="section">
            <div className="section-header">
              <div>
                <h2>OMOP / ETL status</h2>
                <p className="section-copy">
                  This panel shows how incoming source data is translated into the standardized
                  research layer, including snapshot state, ETL metadata, domain loads, and mapping
                  gaps that still need work.
                </p>
              </div>
            </div>

            <div className="omop-grid">
              <article className="omop-card">
                <div className="feed-topline">
                  <div className="omop-label">Current snapshot</div>
                  <span
                    className={`status-chip ${
                      data.omop_etl.current_snapshot.snapshot_status === 'complete'
                        ? 'verified'
                        : 'monitor'
                    }`}
                  >
                    {data.omop_etl.current_snapshot.snapshot_status === 'complete'
                      ? 'Ready'
                      : 'Attention'}
                  </span>
                </div>
                <div className="omop-value">
                  {data.omop_etl.current_snapshot.snapshot_id || '—'}
                </div>
                <div className="kpi-note">
                  Anchored ledger block: {data.omop_etl.current_snapshot.snapshot_block ?? '—'}
                </div>
              </article>

              <article className="omop-card">
                <div className="omop-label">ETL run</div>
                <div className="omop-value">{data.omop_etl.run_context.run_id || '—'}</div>
                <div className="kpi-note">{data.omop_etl.run_context.last_run_at || '—'}</div>
              </article>

              <article className="omop-card">
                <div className="omop-label">Mapping coverage</div>
                <div className="omop-value">
                  {data.omop_etl.current_snapshot.mapping_coverage.toFixed(1)}%
                </div>
                <div className="kpi-note">
                  Prototype source-to-OMOP mapping completeness
                </div>
              </article>

              <article className="omop-card">
                <div className="omop-label">Vocabulary coverage</div>
                <div className="omop-value">
                  {data.omop_etl.current_snapshot.vocabulary_coverage.toFixed(1)}%
                </div>
                <div className="kpi-note">Standardized terminology readiness</div>
              </article>
            </div>
          </section>

          <section className="section two-column">
            <div className="panel">
              <div className="section-header compact">
                <div>
                  <h2>OMOP domain loads</h2>
                  <p className="section-copy">
                    Estimated prototype loads into the main research domains.
                  </p>
                </div>
              </div>

              <div className="ledger-table-wrap">
                <table className="ledger-table">
                  <thead>
                    <tr>
                      <th>Domain</th>
                      <th>Rows</th>
                      <th>Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.omop_etl.domain_loads.map((domain) => (
                      <tr key={domain.domain}>
                        <td>{domain.domain}</td>
                        <td>{domain.rows}</td>
                        <td>{domain.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="panel">
              <div className="section-header compact">
                <div>
                  <h2>ETL run context</h2>
                  <p className="section-copy">
                    Current target model, ETL configuration, and known gaps before analysis-grade
                    use.
                  </p>
                </div>
              </div>

              <div className="omop-meta">
                <div className="feed-meta-row">
                  <span>Target CDM</span>
                  <strong>{data.omop_etl.run_context.target_cdm || '—'}</strong>
                </div>
                <div className="feed-meta-row">
                  <span>ETL spec version</span>
                  <strong>{data.omop_etl.run_context.etl_spec_version || '—'}</strong>
                </div>
                <div className="feed-meta-row">
                  <span>Vocabulary release</span>
                  <strong>{data.omop_etl.run_context.vocabulary_release || '—'}</strong>
                </div>
                <div className="feed-meta-row">
                  <span>Quality gate pass rate</span>
                  <strong>
                    {data.omop_etl.current_snapshot.quality_gate_pass_rate.toFixed(1)}%
                  </strong>
                </div>
              </div>

              <div className="omop-gap-block">
                <h3>Mapping gaps</h3>
                <ul className="finding-list">
                  {data.omop_etl.mapping_gaps.map((gap) => (
                    <li key={gap}>{gap}</li>
                  ))}
                </ul>
              </div>
            </div>
          </section>

          <section className="section">
            <div className="section-header">
              <div>
                <h2>Data lifecycle flow</h2>
                <p className="section-copy">
                  This reflects actual runtime behavior in the prototype.
                </p>
              </div>
            </div>
            <div className="lifecycle-grid">
              {data.data_lifecycle.map((stage, index) => (
                <article key={stage.step} className={`lifecycle-card ${stage.status}`}>
                  <div className="lifecycle-topline">
                    <span className="stage-number">0{stage.step}</span>
                    <span className={`status-pill ${stage.status}`}>{stage.status}</span>
                  </div>
                  <h3>{stage.title}</h3>
                  <p className="stage-description">{stage.description}</p>
                  <ul className="check-list">
                    {stage.checks.map((check) => (
                      <li key={check}>{check}</li>
                    ))}
                  </ul>
                  {index < data.data_lifecycle.length - 1 ? (
                    <div className="stage-arrow">→</div>
                  ) : null}
                </article>
              ))}
            </div>
          </section>

          <section className="section two-column">
            <div className="panel">
              <div className="section-header compact">
                <div>
                  <h2>Simulated blockchain ledger</h2>
                  <p className="section-copy">
                    Every dataset, patient, and visit creates a new append-only record with block
                    number, signer, timestamp, and artifact hash.
                  </p>
                </div>
              </div>
              <div className="ledger-table-wrap">
                <table className="ledger-table">
                  <thead>
                    <tr>
                      <th>Block</th>
                      <th>Artifact</th>
                      <th>Event</th>
                      <th>Hash</th>
                      <th>Signer</th>
                      <th>Timestamp</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedLedger.map((entry) => (
                      <tr key={entry.block}>
                        <td>{entry.block}</td>
                        <td>{entry.artifact}</td>
                        <td>{entry.event}</td>
                        <td className="mono">{entry.hash.slice(0, 18)}...</td>
                        <td>{entry.signer}</td>
                        <td>{entry.timestamp}</td>
                        <td>
                          <span className="status-chip verified">{entry.status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="panel stack-panel">
              <div className="section-header compact">
                <div>
                  <h2>Open findings</h2>
                  <p className="section-copy">
                    These findings now include patient-level missing HBV variables and temporal
                    issues.
                  </p>
                </div>
              </div>
              <ul className="finding-list">
                {data.quality.open_findings.map((finding) => (
                  <li key={finding}>{finding}</li>
                ))}
              </ul>
            </div>
          </section>

          <section className="section">
            <div className="section-header">
              <div>
                <h2>Recent dataset submissions</h2>
                <p className="section-copy">Dataset-level artifacts stored in the backend.</p>
              </div>
            </div>
            <div className="panel">
              <div className="ledger-table-wrap">
                <table className="ledger-table">
                  <thead>
                    <tr>
                      <th>Created</th>
                      <th>Site</th>
                      <th>Source</th>
                      <th>Country</th>
                      <th>HBV cohort</th>
                      <th>Bepirovirsen</th>
                      <th>DQ</th>
                      <th>Block</th>
                      <th>File</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {submissions.map((submission) => (
                      <tr key={submission.id}>
                        <td>{submission.created_at}</td>
                        <td>{submission.site_name}</td>
                        <td>{submission.source_type}</td>
                        <td>{submission.country}</td>
                        <td>{submission.hbv_cohort}</td>
                        <td>{submission.bepirovirsen_treated}</td>
                        <td>{submission.dq_score}</td>
                        <td>{submission.ledger_block}</td>
                        <td>{submission.file_name || '—'}</td>
                        <td>
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() =>
                              void verifyEndpoint(
                                `${API_BASE}/prototype/submissions/${submission.id}/verify`,
                                `Submission ${submission.id}`
                              )
                            }
                          >
                            Verify
                          </button>
                        </td>
                      </tr>
                    ))}
                    {submissions.length === 0 ? (
                      <tr>
                        <td colSpan={10}>No dataset submissions yet.</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <section className="section">
            <div className="section-header">
              <div>
                <h2>HBV patient registry</h2>
                <p className="section-copy">
                  Structured baseline patient records stored in the prototype.
                </p>
              </div>
            </div>
            <div className="panel">
              <div className="ledger-table-wrap">
                <table className="ledger-table">
                  <thead>
                    <tr>
                      <th>Created</th>
                      <th>Pseudonym</th>
                      <th>Site</th>
                      <th>Country</th>
                      <th>Dx date</th>
                      <th>HBsAg</th>
                      <th>HBV DNA</th>
                      <th>ALT</th>
                      <th>NA</th>
                      <th>Bepi</th>
                      <th>Visits</th>
                      <th>Block</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {patients.map((patient) => (
                      <tr key={patient.id}>
                        <td>{patient.created_at}</td>
                        <td>{patient.patient_pseudonym}</td>
                        <td>{patient.site_name}</td>
                        <td>{patient.country}</td>
                        <td>{patient.diagnosis_date}</td>
                        <td>{formatNullable(patient.baseline_hbsag)}</td>
                        <td>{formatNullable(patient.baseline_hbv_dna)}</td>
                        <td>{formatNullable(patient.baseline_alt)}</td>
                        <td>{patient.on_na_therapy ? 'Yes' : 'No'}</td>
                        <td>
                          {patient.started_bepirovirsen
                            ? 'Started'
                            : patient.bepirovirsen_eligible
                            ? 'Eligible'
                            : 'No'}
                        </td>
                        <td>{patient.visit_count}</td>
                        <td>{patient.ledger_block}</td>
                        <td>
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() =>
                              void verifyEndpoint(
                                `${API_BASE}/prototype/patients/${patient.id}/verify`,
                                `Patient ${patient.patient_pseudonym}`
                              )
                            }
                          >
                            Verify
                          </button>
                        </td>
                      </tr>
                    ))}
                    {patients.length === 0 ? (
                      <tr>
                        <td colSpan={13}>No patient records yet.</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <section className="section">
            <div className="section-header">
              <div>
                <h2>Longitudinal visits</h2>
                <p className="section-copy">Follow-up records linked to registered patients.</p>
              </div>
            </div>
            <div className="panel">
              <div className="ledger-table-wrap">
                <table className="ledger-table">
                  <thead>
                    <tr>
                      <th>Created</th>
                      <th>Patient</th>
                      <th>Visit date</th>
                      <th>Type</th>
                      <th>HBsAg</th>
                      <th>HBV DNA</th>
                      <th>ALT</th>
                      <th>NA</th>
                      <th>Bepi</th>
                      <th>Cure endpoint</th>
                      <th>Block</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allVisits.map((visit) => (
                      <tr key={visit.id}>
                        <td>{visit.created_at}</td>
                        <td>{visit.patient_pseudonym}</td>
                        <td>{visit.visit_date}</td>
                        <td>{visit.visit_type}</td>
                        <td>{formatNullable(visit.quantitative_hbsag)}</td>
                        <td>{formatNullable(visit.hbv_dna)}</td>
                        <td>{formatNullable(visit.alt)}</td>
                        <td>{visit.on_na_therapy ? 'Yes' : 'No'}</td>
                        <td>{visit.on_bepirovirsen ? 'Yes' : 'No'}</td>
                        <td>{visit.functional_cure_endpoint ? 'Yes' : 'No'}</td>
                        <td>{visit.ledger_block}</td>
                        <td>
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() =>
                              void verifyEndpoint(
                                `${API_BASE}/prototype/patients/${visit.patient_id}/visits/${visit.id}/verify`,
                                `Visit ${visit.id}`
                              )
                            }
                          >
                            Verify
                          </button>
                        </td>
                      </tr>
                    ))}
                    {allVisits.length === 0 ? (
                      <tr>
                        <td colSpan={12}>No visit records yet.</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <section className="section two-column">
            <div className="panel chart-panel">
              <div className="section-header compact">
                <div>
                  <h2>Quality dimensions</h2>
                  <p className="section-copy">
                    Live dimensions derived from the current artifact store.
                  </p>
                </div>
              </div>
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data.quality.dimensions}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Bar dataKey="score" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="panel chart-panel">
              <div className="section-header compact">
                <div>
                  <h2>Issue severity profile</h2>
                  <p className="section-copy">
                    Issues are recalculated when datasets, patients, or visits change.
                  </p>
                </div>
              </div>
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data.quality.issue_severity}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="severity" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          <section className="section two-column">
            <div className="panel chart-panel">
              <div className="section-header compact">
                <div>
                  <h2>Readiness trend</h2>
                  <p className="section-copy">The last stored artifacts drive this trend.</p>
                </div>
              </div>
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={data.quality.readiness_trend}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis domain={[60, 100]} />
                    <Tooltip />
                    <Line type="monotone" dataKey="score" strokeWidth={3} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="panel chart-panel">
              <div className="section-header compact">
                <div>
                  <h2>Source coverage</h2>
                  <p className="section-copy">
                    Counts are aggregated directly from datasets and clinician-entry artifacts.
                  </p>
                </div>
              </div>
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data.quality.source_coverage}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="source" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="records" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

          <section className="section two-column">
            <div className="panel">
              <div className="section-header compact">
                <div>
                  <h2>Readiness matrix</h2>
                  <p className="section-copy">
                    Computed from the current data in the prototype store.
                  </p>
                </div>
              </div>
              <div className="readiness-grid">
                {data.trial_readiness.map((item) => (
                  <article key={item.criterion} className="readiness-card">
                    <div className="readiness-topline">
                      <strong>{item.criterion}</strong>
                      <span
                        className={`status-chip ${
                          item.status === 'Pass' ? 'verified' : 'monitor'
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>
                    <p>{item.detail}</p>
                  </article>
                ))}
              </div>
            </div>

            <div className="panel">
              <div className="section-header compact">
                <div>
                  <h2>Next steps</h2>
                  <p className="section-copy">Logical upgrades after the prototype round.</p>
                </div>
              </div>
              <ol className="next-step-list">
                {data.next_steps.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

export default App;