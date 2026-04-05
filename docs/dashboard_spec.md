# Dashboard Specification

## Primary users
- Clinical evidence leads
- Medical affairs / RWE teams
- Data stewards
- Privacy and compliance reviewers
- Site operations managers

## Pages

### 1. Overview
Cards:
- Total HBV patients
- Bepirovirsen-treated patients
- Latest snapshot date
- Overall DQ score
- Blockchain verification status

Charts:
- Patient growth by month
- Source contribution by system
- Open critical data issues

### 2. Cohort explorer
Filters:
- country
- site
- age band
- sex
- NA therapy status
- bepirovirsen exposure
- HBsAg baseline band
- HBV DNA status
- HBeAg status

Outputs:
- cohort counts
- export request button with approval workflow
- variable completeness panel

### 3. Patient journey
Panels:
- visit timeline
- treatment periods
- labs trend chart for HBsAg / HBV DNA / ALT / AST
- alerts: missing visit, discordant temporal logic, possible flare, possible cure signal

### 4. Quality and provenance
Widgets:
- missingness heatmap
- rule failures by source and variable
- ETL version history
- last notarized artifact list
- verify proof action

### 5. Governance
- record of processing entries
- DPIA status
- model registry
- access approvals
- export log

## Key KPIs
- completeness rate for HBsAg, HBV DNA, ALT
- median time between follow-ups
- proportion with sustained undetectable HBV DNA
- proportion with HBsAg below detection limit
- ALT normalization rate
- adherence proxy coverage
- % records linked across >= 2 sources
