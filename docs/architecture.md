# Architecture Blueprint

## 1. Core principles

- **Data minimization**: only research-permitted variables move to the analytics environment.
- **Separation of concerns**: identifiers, linkage secrets, analytics, and provenance live in different trust zones.
- **OMOP-first analytics**: standardized data model and vocabularies drive reproducible analysis.
- **Immutable provenance**: blockchain records prove snapshot integrity and pipeline lineage.
- **Privacy by design**: pseudonymization, role-based access, and non-PHI blockchain policy.

## 2. Trust zones

### Zone A: Source systems
Hospitals, labs, pharmacy systems, imaging, and claims-like datasets.

### Zone B: Secure landing
Encrypted object store for inbound files with:
- checksum verification
- schema profiling
- malware scanning
- signed transfer receipts

### Zone C: Linkage enclave
Used only for privacy-preserving record linkage (PPRL).
Contains:
- salt / pepper secrets
- tokenization jobs
- source-to-OMOP person crosswalks

### Zone D: Analytics platform
Contains:
- raw staging
- OMOP PostgreSQL
- validation services
- cohort APIs
- dashboard services

### Zone E: Provenance ledger
Permissioned Fabric network where peers belong to trusted parties such as sponsor, data custodian, and auditor nodes.
Stores only:
- SHA-256 / SHA-3 hashes of dataset manifests and reports
- ETL spec versions
- AI model version IDs
- signer identity
- timestamps
- run status

## 3. End-to-end data flow

1. Source file arrives in landing zone.
2. File is checksummed and registered.
3. PPRL service generates linkage tokens from approved quasi-identifiers in the enclave.
4. ETL maps raw fields to OMOP.
5. OMOP snapshot is versioned.
6. Data quality rules and AI-assisted validators run.
7. A manifest of outputs is hashed.
8. Hashes and run metadata are notarized on the permissioned ledger.
9. Dashboard reads OMOP, quality outputs, and ledger proofs.

## 4. Logical services

### Ingestion service
Responsibilities:
- receive files and API pushes
- validate schema and delivery contract
- record landing metadata
- queue ETL jobs

### PPRL service
Responsibilities:
- generate deterministic or probabilistic privacy-preserving linkage keys
- resolve source identities to a stable research person_id
- keep re-identification assets separate from analytics consumers

### OMOP ETL service
Responsibilities:
- map demographics, conditions, procedures, measurements, drugs, visits, and observations
- use standard vocabularies where available
- emit versioned snapshot manifest

### Validation engine
Responsibilities:
- run rules for completeness, conformance, plausibility, temporal logic, and HBV-specific clinical consistency
- produce issue lists and severity scores

### Notary service
Responsibilities:
- collect artifact hashes
- write notarization transaction to Fabric
- verify proof for audits and dashboard display

### Analytics API
Responsibilities:
- serve cohort metrics
- patient journey timelines
- treatment monitoring metrics
- provenance evidence

## 5. Dashboard modules

1. **Executive overview**
   - active HBV cohort
   - bepirovirsen-exposed cohort
   - completeness index
   - data freshness
   - open critical issues

2. **HBV cascade**
   - screened
   - confirmed chronic HBV
   - on NA therapy
   - bepirovirsen eligible
   - started bepirovirsen
   - functional cure endpoint achieved

3. **Patient journey**
   - longitudinal measurement trends
   - treatment timeline
   - alerts for missing follow-up or implausible values

4. **Data quality and integrity**
   - missingness heatmap
   - failed checks by source
   - latest blockchain proof
   - ETL version lineage

5. **Governance and audit**
   - who accessed what
   - which dataset version powered a result
   - sign-off status
   - exportable audit packet

## 6. Non-functional requirements

- p95 API latency < 500 ms for standard dashboard queries
- monthly source refresh, with weekly supported if source operations allow
- zero PHI on chain
- complete audit trail for create, read, transform, export, and approval actions
- tenant isolation if multiple hospitals contribute data
- encrypted backups and tested restore procedures

## 7. Reference technology choices

- Backend: FastAPI / Python
- Database: PostgreSQL 16
- Ledger: Hyperledger Fabric
- Frontend: React + TypeScript
- ETL orchestration: Prefect or Airflow
- Validation / ML: Python, dbt optional, notebook-free production pipelines
- Identity: OIDC / SAML

## 8. Decision rationale for Fabric

Fabric is a strong fit because the network is permissioned, participants have known identities, and privacy can be enforced with channels and private data collections. That matches regulated multi-party healthcare provenance much better than a public chain.
