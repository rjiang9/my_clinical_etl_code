import json
import dateparser
from clinical_etl.schema import BaseSchema, ValidationError


"""
A class for the representation of a DonorWithClinicalData (MoHCCN data model v2) object in Katsu.
"""

class MoHSchemaV3(BaseSchema):
    schema_name = "DonorWithClinicalDataSchema"
    base_name = "DONOR"

    ## Following are specific checks for required fields in the MoH data model, as well as checks for conditionals specified in the model.
    validation_schema = {
        "donors": {
            "id": "submitter_donor_id",
            "name": "Donor",
            "required_fields": [
                "submitter_donor_id",
                "gender",
                "sex_at_birth",
                "is_deceased",
                "program_id",
                "date_resolution",
                "date_of_birth",
            ],
            "nested_schemas": [
                "primary_diagnoses",
                "comorbidities",
                "exposures",
                "biomarkers",
                "followups"
            ]
        },
        "primary_diagnoses": {
            "id": "submitter_primary_diagnosis_id",
            "name": "Primary Diagnosis",
            "required_fields": [
                "submitter_primary_diagnosis_id",
                "date_of_diagnosis",
                "cancer_type_code",
                "primary_site",
                "basis_of_diagnosis",
            ],
            "nested_schemas": [
                "specimens",
                "treatments",
                "biomarkers",
                "followups"
            ]
        },
        "specimens": {
            "id": "submitter_specimen_id",
            "name": "Specimen",
            "required_fields": [
                "submitter_specimen_id",
                "specimen_collection_date",
                "specimen_storage",
                "specimen_anatomic_location"
            ],
            "nested_schemas": [
                "sample_registrations",
                "biomarkers"
            ]
        },
        "sample_registrations": {
            "id": "submitter_sample_id",
            "name": "Sample Registration",
            "required_fields": [
                "submitter_sample_id",
                "specimen_tissue_source",
                "specimen_type",
                "sample_type"
            ],
            "nested_schemas": []
        },
        "treatments": {
            "id": "submitter_treatment_id",
            "name": "Treatment",
            "required_fields": [
                "submitter_treatment_id",
                "treatment_type",
                "is_primary_treatment",
                "treatment_start_date",
                "treatment_end_date",
                "treatment_intent",
            ],
            "nested_schemas": [
                "systemic_therapies",
                "radiations",
                "surgeries",
                "followups",
                "biomarkers"
            ]
        },
        "systemic_therapies": {
            "id": None,
            "name": "Systemic Therapy",
            "required_fields": [
                "systemic_therapy_type",
                "start_date",
                "end_date",
                "drug_reference_database",
                "drug_reference_identifier",
                "drug_name",
            ],
            "nested_schemas": [],
        },
        "radiations": {
            "id": None,
            "name": "Radiation",
            "required_fields": [
                "radiation_therapy_modality",
                "radiation_therapy_type",
                "anatomical_site_irradiated",
                "radiation_therapy_fractions",
                "radiation_therapy_dosage"
            ],
            "nested_schemas": []
        },
        "surgeries": {
            "id": None,
            "name": "Surgery",
            "required_fields": [
                "surgery_reference_database",
                "surgery_reference_identifier",
                "surgery_type"
            ],
            "nested_schemas": []
        },
        "biomarkers": {
            "id": None,
            "name": "Biomarker",
            "required_fields": [],
            "nested_schemas": []
        },
        "followups": {
            "id": "submitter_follow_up_id",
            "name": "Follow Up",
            "required_fields": [
                "submitter_follow_up_id",
                "date_of_followup",
                "disease_status_at_followup"
            ],
            "nested_schemas": [
                "biomarkers"
            ]
        },
        "comorbidities": {
            "id": None,
            "name": "Comorbidity",
            "required_fields": [
                "comorbidity_type_code"
            ],
            "nested_schemas": []
        },
        "exposures": {
            "id": None,
            "name": "Exposure",
            "required_fields": [],
            "nested_schemas": []
        }
    }

    def validate_donors(self, map_json):
        for prop in map_json:
            match prop:
                case "is_deceased":
                    if map_json["is_deceased"] == "Yes":
                        if "cause_of_death" not in map_json:
                            self.warn("cause_of_death required if is_deceased = Yes")
                        if "date_of_death" not in map_json:
                            self.warn("date_of_death required if is_deceased = Yes")
                case "lost_to_followup_after_clinical_event_identifier":
                    if map_json["lost_to_followup_after_clinical_event_identifier"] is not None:
                        if map_json["is_deceased"] == "Yes":
                            self.fail(
                                "lost_to_followup_after_clinical_event_identifier cannot be present if is_deceased = Yes")
                case "lost_to_followup_reason":
                    if map_json["lost_to_followup_reason"] is not None:
                        if "lost_to_followup_after_clinical_event_identifier" not in map_json:
                            self.fail(
                                "lost_to_followup_reason should only be submitted if lost_to_followup_after_clinical_event_identifier is submitted")
                case "date_alive_after_lost_to_followup":
                    if map_json["date_alive_after_lost_to_followup"] is not None:
                        if "lost_to_followup_after_clinical_event_identifier" not in map_json:
                            self.warn(
                                "lost_to_followup_after_clinical_event_identifier is required if date_alive_after_lost_to_followup is submitted")
                case "cause_of_death":
                    if map_json["cause_of_death"] is not None:
                        if map_json["is_deceased"] in ["No", "Not available"]:
                            self.fail("cause_of_death should only be submitted if is_deceased = Yes")
                case "primary_diagnoses":
                    birth = None
                    death = None
                    if len(map_json["primary_diagnoses"]) > 0:
                        if "date_of_birth" in map_json and map_json["date_of_birth"] not in [None, '']:
                            if "dict" in str(type(map_json["date_of_birth"])):
                                birth = map_json["date_of_birth"]["month_interval"]
                            else:
                                birth = dateparser.parse(map_json["date_of_birth"]).date()
                        if "date_of_death" in map_json and map_json["date_of_death"] not in [None, '']:
                            if "dict" in str(type(map_json["date_of_death"])):
                                death = map_json["date_of_death"]["month_interval"]
                            else:
                                death = dateparser.parse(map_json["date_of_death"]).date()
                        diagnoses_dates = {}
                        for diagnosis in map_json["primary_diagnoses"]:
                            diagnosis_date = None
                            if "date_of_diagnosis" in diagnosis and diagnosis["date_of_diagnosis"] not in [None, '']:
                                if "dict" in str(type(diagnosis["date_of_diagnosis"])):
                                    diagnosis_date = diagnosis["date_of_diagnosis"]["month_interval"]
                                else:
                                    diagnosis_date = dateparser.parse(diagnosis["date_of_diagnosis"]).date()
                                diagnoses_dates[diagnosis['submitter_primary_diagnosis_id']] = diagnosis_date
                                if 'death' in locals() and death not in [None, ''] and diagnosis_date > death:
                                    self.fail(f"{diagnosis['submitter_primary_diagnosis_id']}: date_of_death cannot be earlier than date_of_diagnosis")
                                if 'birth' in locals() and birth not in [None, ''] and diagnosis_date < birth:
                                    self.fail(f"{diagnosis['submitter_primary_diagnosis_id']}: date_of_birth cannot be later than date_of_diagnosis")
                            if "treatments" in diagnosis and len(diagnosis["treatments"]) > 0:
                                for treatment in diagnosis["treatments"]:
                                    treatment_start = None
                                    treatment_end = None
                                    if "treatment_start_date" in treatment and treatment["treatment_start_date"] not in [None, '']:
                                        if "dict" in str(type(treatment["treatment_start_date"])):
                                            treatment_start = treatment["treatment_start_date"]['month_interval']
                                        else:
                                            treatment_start = dateparser.parse(treatment["treatment_start_date"]).date()
                                    if "treatment_end_date" in treatment and treatment["treatment_end_date"] not in [None, '']:
                                        if "dict" in str(type(treatment["treatment_end_date"])):
                                            treatment_end = treatment["treatment_end_date"]['month_interval']
                                        else:
                                            treatment_end = dateparser.parse(treatment["treatment_end_date"]).date()
                                    if ('death' in locals() and death not in [None, ''] and
                                            'treatment_end' in locals() and treatment_end not in [None, '']
                                            and treatment_end > death):
                                        self.fail(f"{diagnosis['submitter_primary_diagnosis_id']} > {treatment['submitter_treatment_id']}: date_of_death cannot be earlier than treatment_end_date ")
                                    if ('diagnosis_date' in locals() and diagnosis_date not in [None, ''] and
                                            treatment_end not in [None, ''] and 'treatment_end' in locals() and
                                            treatment_end < diagnosis_date):
                                        self.warn(f"{diagnosis['submitter_primary_diagnosis_id']} > {treatment['submitter_treatment_id']}: date_of_diagnosis should be earlier than treatment_end_date ")
                                    if 'treatment_start' in locals() and treatment_start not in [None, '']:
                                        if 'death' in locals() and death not in [None, ''] and treatment_start > death:
                                            self.fail(
                                                    f"{diagnosis['submitter_primary_diagnosis_id']} > {treatment['submitter_treatment_id']}: treatment_start_date cannot be after date_of_death ")
                                        if 'birth' in locals() and birth not in [None, ''] and treatment_start < birth and treatment_start is not None:
                                            self.fail(f"{diagnosis['submitter_primary_diagnosis_id']} > {treatment['submitter_treatment_id']}: treatment_start_date cannot be before date_of_birth")
                                        if 'diagnosis_date' in locals() and diagnosis_date not in [None, ''] and treatment_start < diagnosis_date:
                                            self.warn(f"{diagnosis['submitter_primary_diagnosis_id']} > {treatment['submitter_treatment_id']}: treatment_start_date should not be before date_of_diagnosis")
                        diagnosis_values_list = list(diagnoses_dates.values())
                        if (len(diagnosis_values_list) > 0 and "int" in str(type(diagnosis_values_list[0])) and
                                0 not in diagnosis_values_list):
                            self.warn(f"Earliest primary_diagnosis.date_of_diagnosis.month_interval should be 0, current "
                                      f"month_intervals: {diagnoses_dates}")
                case "date_of_death":
                    if map_json["date_of_death"] is not None:
                        if map_json["is_deceased"] in ["No", "Not available"]:
                            self.fail("date_of_death should only be submitted if is_deceased = Yes")
                    if map_json["date_of_birth"] is not None and map_json["date_of_death"] is not None:
                        if "dict" in str(type(map_json["date_of_birth"])):
                            death = map_json["date_of_death"]["month_interval"]
                            birth = map_json["date_of_birth"]["month_interval"]
                            if ("date_alive_after_lost_to_followup" in map_json and
                                    map_json["date_alive_after_lost_to_followup"] is not None):
                                date_alive = map_json["date_alive_after_lost_to_followup"]["month_interval"]
                        else:
                            death = dateparser.parse(map_json["date_of_death"]).date()
                            birth = dateparser.parse(map_json["date_of_birth"]).date()
                            if ("date_alive_after_lost_to_followup" in map_json and
                                    map_json["date_alive_after_lost_to_followup"] is not None):
                                date_alive = dateparser.parse(
                                    map_json["date_alive_after_lost_to_followup"]).date()
                        if birth > death:
                            self.fail("date_of_death cannot be earlier than date_of_birth")
                        if "date_alive_after_lost_to_followup" in map_json and date_alive > death:
                            self.fail("date_alive_after_lost_to_followup cannot be after date_of death")
                        if "date_alive_after_lost_to_followup" in map_json and date_alive < birth:
                            self.fail("date_alive_after_lost_to_followup cannot be before date_of birth")
                case "biomarkers":
                    for x in map_json["biomarkers"]:
                        if "test_date" not in x or x["test_date"] is None:
                            self.warn("test_date is required for biomarkers not associated with nested events")

    def validate_primary_diagnoses(self, map_json):
        if "clinical_tumour_staging_system" not in map_json and "pathological_staging_system" not in map_json:
            self.warn("Either clinical_tumour_staging_system or pathological_staging_system is required")

        for prop in map_json:
            if prop == "clinical_tumour_staging_system":
                self.validate_staging_system(map_json, "clinical")
            elif prop == "pathological_tumour_staging_system":
                self.validate_staging_system(map_json, "pathological")

    def validate_staging_system(self, map_json, staging_type):
        if "AJCC" in map_json[f"{staging_type}_tumour_staging_system"]:
            required_fields = [
                "t_category",
                "n_category",
                "m_category"
            ]
            for f in required_fields:
                if f"{staging_type}_{f}" not in map_json or map_json[f"{staging_type}_{f}"] is None:
                    self.warn(f"{staging_type}_{f} is required if {staging_type}_tumour_staging_system is AJCC")
        else:
            if f"{staging_type}_stage_group" not in map_json or map_json[f"{staging_type}_stage_group"] is None:
                self.warn(f"{staging_type}_stage_group is required for {staging_type}_tumour_staging_system {map_json[f'{staging_type}_tumour_staging_system']}")

    def validate_specimens(self, map_json):
        if "samples" in map_json:
            for sample in map_json["samples"]:
                if "tumour_normal_designation" in sample and sample["tumour_normal_designation"] == "Tumour":
                    required_fields = [
                        "reference_pathology_confirmed_diagnosis",
                        "reference_pathology_confirmed_tumour_presence",
                        "tumour_grading_system",
                        "tumour_grade",
                        "percent_tumour_cells_range",
                        "percent_tumour_cells_measurement_method"
                    ]
                    for f in required_fields:
                        if f not in map_json:
                            self.warn(f"Tumour specimens require a {f}")

    def validate_sample_registrations(self, map_json):
        # there aren't any additional validations here
        return

    def validate_treatments(self, map_json):
        for prop in map_json:
            if prop == "treatment_type" and map_json["treatment_type"] is not None:
                for t_type in map_json["treatment_type"]:
                    match t_type:
                        case "Systemic therapy":
                            if "systemic_therapies" not in map_json or len(map_json["systemic_therapies"]) == 0:
                                self.warn("Treatment type Systemic therapy should have one or more systemic therapies submitted")
                        case "Radiation therapy":
                            if "radiations" not in map_json or len(map_json["radiations"]) == 0:
                                self.warn("Treatment type Radiation therapy should have one or more radiation submitted")
                        case "Surgery":
                            if "surgeries" not in map_json or len(map_json["surgeries"]) == 0:
                                self.warn("Treatment type Surgery should have one or more surgery submitted")
            elif prop == "treatment_start_date" and map_json["treatment_start_date"] is not None:
                if "treatment_end_date" in map_json and map_json["treatment_end_date"] is not None:
                    if "dict" in str(type(map_json["treatment_start_date"])):
                        treatment_start = map_json["treatment_start_date"]["month_interval"]
                        treatment_end = map_json["treatment_end_date"]["month_interval"]
                    else:
                        treatment_start = dateparser.parse(map_json["treatment_start_date"]).date()
                        treatment_end = dateparser.parse(map_json["treatment_end_date"]).date()
                    if treatment_start > treatment_end:
                        self.fail("Treatment start cannot be after treatment end.")
                    
                    if "systemic_therapies" in map_json and len(map_json["systemic_therapies"]) > 0:
                        for therapy in map_json["systemic_therapies"]:
                            if "start_date" in therapy and therapy["start_date"] not in [None, '']:
                                if "dict" in str(type(therapy["start_date"])):
                                    therapy_start = therapy["start_date"]['month_interval']
                                else:
                                    therapy_start = dateparser.parse(therapy["start_date"]).date()
                                if therapy_start < treatment_start:
                                    self.fail(
                                        "Systemic therapy start date cannot be earlier than its treatment start date.")
                            if "end_date" in therapy and therapy["end_date"] not in [None, '']:
                                if "dict" in str(type(therapy["end_date"])):
                                    therapy_end = therapy["end_date"]["month_interval"]
                                else:
                                    therapy_end = dateparser.parse(therapy["treatment_end_date"]).date()
                                if therapy_end > treatment_end:
                                    self.fail("Systemic therapy end date cannot be after its treatment end date.")

    def validate_systemic_therapies(self, map_json):
        if "drug_dose_units" not in map_json or map_json["drug_dose_units"] is None:
            for x in ["prescribed_cumulative_drug_dose", "actual_cumulative_drug_dose"]:
                if x in map_json and map_json[x] is not None:
                    self.warn(f"drug_dose_units required if {x} is submitted")
        for prop in map_json:
            if prop == "start_date" and map_json["start_date"] is not None:
                start = None
                end = None
                if "end_date" in map_json and map_json["end_date"] is not None:
                    if "dict" in str(type(map_json["start_date"])):
                        if "month_interval" in map_json["start_date"]:
                            start = map_json["start_date"]["month_interval"]
                        if "month_interval" in map_json["end_date"]:
                            end = map_json["end_date"]["month_interval"]
                    else:
                        start = dateparser.parse(map_json["start_date"]).date()
                        end = dateparser.parse(map_json["end_date"]).date()
                    if start and end and start > end:
                        self.fail("Systemic therapy start cannot be after systemic therapy end.")

    def validate_radiations(self, map_json):
        for prop in map_json:
            if prop == "radiation_boost" and map_json["radiation_boost"] == "Yes":
                if "reference_radiation_treatment_id" not in map_json or map_json["reference_radiation_treatment_id"] is None:
                    self.warn("reference_radiation_treatment_id required if radiation_boost = Yes")

    def validate_surgeries(self, map_json):
        # No validations needed (submitter_specimen_id removed in V3)
        return

    def validate_followups(self, map_json):
        for prop in map_json:
            if prop == "disease_status_at_followup":
                states = [
                    "Distant progression",
                    "Loco-regional progression",
                    "Progression not otherwise specified",
                    "Relapse or recurrence"
                ]
                if map_json["disease_status_at_followup"] in states:
                    required_fields = [
                        "relapse_type",
                        "date_of_relapse",
                        "method_of_progression_status"
                    ]
                    for field in required_fields:
                        if field not in map_json:
                            self.warn(f"{field} is required if disease_status_at_followup is {map_json['disease_status_at_followup']}")
                    if "anatomic_site_progression_or_recurrence" not in map_json:
                        if "relapse_type" in map_json and map_json["relapse_type"] != "Biochemical progression":
                            self.warn(f"anatomic_site_progression_or_recurrence is required if disease_status_at_followup is {map_json['disease_status_at_followup']}")

    def validate_biomarkers(self, map_json):
        for prop in map_json:
            match prop:
                case "hpv_pcr_status":
                    if map_json["hpv_pcr_status"] == "Positive" and "hpv_strain" not in map_json:
                        self.warn("If hpv_pcr_status is positive, hpv_strain is required")

    def validate_comorbidities(self, map_json):
        for prop in map_json:
            if prop == "laterality_of_prior_malignancy":
                if "prior_malignancy" not in map_json or map_json["prior_malignancy"] != "Yes":
                    self.fail("laterality_of_prior_malignancy should not be submitted unless prior_malignancy = Yes")

    def validate_exposures(self, map_json):
        is_smoker = False
        if "tobacco_smoking_status" not in map_json or map_json["tobacco_smoking_status"] is None:
            self.warn("tobacco_smoking_status required for exposure")
        else:
            if map_json["tobacco_smoking_status"] in [
                "Current reformed smoker for <= 15 years",
                "Current reformed smoker for > 15 years",
                "Current reformed smoker, duration not specified",
                "Current smoker"
            ]:
                is_smoker = True

            for prop in map_json:
                if prop == "tobacco_type":
                    if not is_smoker:
                        self.fail(f"tobacco_type cannot be submitted for tobacco_smoking_status = {map_json['tobacco_smoking_status']}")
                elif prop == "pack_years_smoked":
                    if not is_smoker:
                        self.fail(f"pack_years_smoked cannot be submitted for tobacco_smoking_status = {map_json['tobacco_smoking_status']}")
