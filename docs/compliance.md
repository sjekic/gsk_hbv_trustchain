# Compliance Blueprint

## Important note
This is an engineering interpretation for solution design. It is **not legal advice** and should be reviewed by GSK legal counsel, the data protection officer, security, quality assurance, and study governance teams.

## 1. GDPR control map

### Article 5 principles
Controls:
- purpose-specific processing registry
- source-level field allowlists
- automatic retention schedules
- immutable provenance for accountability
- quality monitoring for accuracy and integrity

### Articles 6 and 9 lawful basis / special category data
Controls:
- documented lawful basis per data source and country
- Article 9 condition documented before onboarding any health data feed
- secondary use approval workflow and contract registry

### Article 25 data protection by design and by default
Controls:
- pseudonymization before analytics access
- role-scoped views
- masked exports
- disabled ad hoc raw record downloads by default

### Article 30 records of processing activities
Controls:
- maintain machine-readable RoPA in governance schema
- tie each pipeline, dataset, and purpose to the processing record

### Article 32 security of processing
Controls:
- encryption at rest and in transit
- key rotation
- PAM / least privilege
- break-glass workflow
- SIEM monitoring and tamper-evident logs

### Article 35 DPIA
Controls:
- mandatory DPIA before first live data ingestion
- material change review for new sources, new AI models, or new export pathways

### Chapter V international transfers
Controls:
- EU-hosted primary environment by default
- transfer assessment gate before any non-EEA processing or support access

## 2. EHDS alignment

EHDS adds a Europe-wide framework for access to and secondary use of electronic health data. For this platform that means:
- keep a clean distinction between primary-use operational systems and secondary-use research analytics
- support standardized, interoperable datasets and metadata
- make data permit and approved-use constraints enforceable in software
- prepare for federated data access patterns rather than assuming unrestricted centralization

Practical controls:
- data-permit metadata on each dataset and export
- policy engine enforcing allowed purpose, user role, country, and project
- federated query mode as a future extension
- standardized metadata catalog for snapshots and data products

## 3. FDA 21 CFR Part 11 alignment

The system should treat key records as regulated electronic records where applicable. Required controls include:
- validated systems and change control
- secure, computer-generated, time-stamped audit trails
- user accountability through unique identities
- controlled e-signature / approval workflows for release and export decisions
- retrievability of records for inspection

## 4. EU AI Act posture

The safest posture is to treat the HBV AI modules as governed, high-scrutiny components and operate them with:
- defined intended use
- human oversight
- risk management file
- traceable training / validation data lineage
- performance monitoring by site and subgroup
- model card and release sign-off
- no fully automated diagnosis or treatment decisions

## 5. Blockchain policy

### Allowed on chain
- artifact hash
- run ID
- signer ID or certificate reference
- event timestamp
- config version IDs
- verification status

### Not allowed on chain
- direct identifiers
- pseudonymous patient-level facts
- free text clinical notes
- lab results
- demographics that could enable re-identification
- encryption keys or secrets

## 6. Validation package before go-live

- URS / functional specs
- IQ / OQ / PQ or equivalent computer system validation evidence
- threat model
- DPIA
- access matrix
- disaster recovery test evidence
- data mapping sign-off
- model validation pack
- SOPs for incident handling, access review, and change control
