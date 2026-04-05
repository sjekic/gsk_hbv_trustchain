# HBV and Bepirovirsen Variable Catalog

## Core patient and journey variables

### Identification and cohorting
- source_system
- source_patient_id (restricted zone only)
- omop_person_id
- chronic_hbv_confirmed_date
- diagnosis_route (screening / symptoms / abnormal labs)
- follow_up_status

### Demographics and context
- birth_year
- sex_at_birth
- country
- site_id
- family_history_liver_cancer
- alcohol_use_status
- comorbidity_flags

### HBV virology and serology
- hbsag_quantitative_value
- hbsag_unit
- hbsag_detectable_flag
- hbv_dna_quantitative_value
- hbv_dna_unit
- hbv_dna_detectable_flag
- hbeag_status

### Liver injury and function
- alt_value
- alt_unit
- alt_uln_value
- alt_below_uln_flag
- ast_value
- bilirubin_value
- albumin_value
- inr_value

### Disease staging and outcomes
- fibrosis_stage_if_available
- cirrhosis_flag
- hcc_flag
- hepatic_decompensation_flag
- functional_cure_endpoint_flag
- functional_cure_assessment_date

### Treatment history
- na_therapy_flag
- na_therapy_start_date
- na_therapy_drug
- adherence_proxy
- bepirovirsen_eligibility_flag
- bepirovirsen_start_date
- bepirovirsen_stop_date
- bepirovirsen_course_completed_flag
- adverse_event_flag
- alt_flare_flag

### Monitoring cadence
- visit_date
- visit_type
- lab_collection_date
- missed_follow_up_flag
- next_recommended_monitoring_date

## Derived metrics
- days_from_chronic_confirmation_to_na
- days_from_na_to_bepirovirsen
- rolling_hbsag_change
- rolling_hbv_dna_change
- treatment_response_class
- data_completeness_score
- provenance_verified_flag

## OMOP table targets (typical)
- PERSON
- VISIT_OCCURRENCE
- CONDITION_OCCURRENCE
- DRUG_EXPOSURE
- MEASUREMENT
- OBSERVATION
- EPISODE / EPISODE_EVENT where appropriate in CDM v5.4
- METADATA and CDM_SOURCE for source and transformation provenance
