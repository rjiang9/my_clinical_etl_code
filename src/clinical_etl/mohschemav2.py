import json
import dateparser
from clinical_etl.schema import BaseSchema, ValidationError


"""
A class for the representation of a DonorWithClinicalData (MoHCCN data model v2) object in Katsu.
"""

class MoHSchemaV2(BaseSchema):
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
                "primary_site"
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
                "basis_of_diagnosis",
                "lymph_nodes_examined_status"
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
                "treatment_setting",
                "treatment_intent",
                "response_to_treatment_criteria_method",
                "response_to_treatment"
            ],
            "nested_schemas": [
                "chemotherapies",
                "hormone_therapies",
                "immunotherapies",
                "radiations",
                "surgeries",
                "followups",
                "biomarkers"
            ]
        },
        "chemotherapies": {
            "id": None,
            "name": "Chemotherapy",
            "required_fields": [
                "drug_reference_database",
                "drug_name",
                "drug_reference_identifier"
            ],
            "nested_schemas": []
        },
        "hormone_therapies": {
            "id": None,
            "name": "Hormone Therapy",
            "required_fields": [
                "drug_reference_database",
                "drug_name",
                "drug_reference_identifier"
            ],
            "nested_schemas": []
        },
        "immunotherapies": {
            "id": None,
            "name": "Immunotherapy",
            "required_fields": [
                "drug_reference_database",
                "drug_name",
                "drug_reference_identifier"
            ],
            "nested_schemas": []
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
                    if map_json["is_deceased"]:
                        if "cause_of_death" not in map_json:
                            self.warn("cause_of_death required if is_deceased = Yes")
                        if "date_of_death" not in map_json:
                            self.warn("date_of_death required if is_deceased = Yes")
                case "lost_to_followup_after_clinical_event_identifier":
                    if map_json["lost_to_followup_after_clinical_event_identifier"] is not None:
                        if map_json["is_deceased"]:
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
                        if not map_json["is_deceased"]:
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
                        if not map_json["is_deceased"]:
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
        # check to see if this primary_diagnosis is a tumour:
        specimen_ids = []
        is_tumour = False
        # should either have a clinical staging system specified
        # OR have a specimen with a pathological staging system specified
        if "clinical_tumour_staging_system" in map_json and map_json["clinical_tumour_staging_system"] is not None:
            is_tumour = True
        if "specimens" in map_json:
            for specimen in map_json["specimens"]:
                specimen_ids.append(specimen["submitter_specimen_id"])
                if "pathological_tumour_staging_system" in specimen and specimen["pathological_tumour_staging_system"] is not None:
                    is_tumour = True

        self.validation_schema["primary_diagnoses"]["extra_args"]["specimen_ids"] = specimen_ids
        self.validation_schema["primary_diagnoses"]["extra_args"]["is_tumour"] = is_tumour

        for prop in map_json:
            match prop:
                case "lymph_nodes_examined_status":
                    if map_json["lymph_nodes_examined_status"]:
                        if "lymph_nodes_examined_method" not in map_json or map_json["lymph_nodes_examined_method"] is None:
                            self.warn("lymph_nodes_examined_method required if lymph_nodes_examined_status = Yes")
                        if "number_lymph_nodes_positive" not in map_json or map_json["number_lymph_nodes_positive"] is None:
                            self.warn("number_lymph_nodes_positive required if lymph_nodes_examined_status = Yes")
                case "clinical_tumour_staging_system":
                    self.validate_staging_system(map_json, "clinical")


    def validate_specimens(self, map_json):
        is_clinical_tumour = self.validation_schema["primary_diagnoses"]["extra_args"]["is_tumour"]
        # Presence of tumour_histological_type means we have a tumour sample
        if "tumour_histological_type" in map_json:
            if not is_clinical_tumour:
                if "pathological_tumour_staging_system" not in map_json or map_json["pathological_tumour_staging_system"] is None:
                    self.warn("Tumour specimens without clinical_tumour_staging_system require a pathological_tumour_staging_system")
                else:
                    self.validate_staging_system(map_json, "pathological")
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


    def validate_biomarkers(self, map_json):
        for prop in map_json:
            match prop:
                case "hpv_pcr_status":
                    if map_json["hpv_pcr_status"] == "Positive" and "hpv_strain" not in map_json:
                        self.warn("If hpv_pcr_status is positive, hpv_strain is required")


    def validate_followups(self, map_json):
        for prop in map_json:
            match prop:
                case "disease_status_at_followup":
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


    def validate_treatments(self, map_json):
        for prop in map_json:
            match prop:
                case "treatment_type":
                    if map_json["treatment_type"] is not None:
                        for t_type in map_json["treatment_type"]:
                            match t_type:
                                case "Chemotherapy":
                                    if "chemotherapies" not in map_json or len(map_json["chemotherapies"]) == 0:
                                        self.warn("treatment type Chemotherapy should have one or more chemotherapies submitted")
                                case "Hormonal therapy":
                                    if "hormone_therapies" not in map_json or len(map_json["hormone_therapies"]) == 0:
                                        self.warn("treatment type Hormonal therapy should have one or more hormone_therapies submitted")
                                case "Immunotherapy":
                                    if "immunotherapies" not in map_json or len(map_json["immunotherapies"]) == 0:
                                        self.warn("treatment type Immunotherapy should have one or more immunotherapies submitted")
                                case "Radiation therapy":
                                    if "radiations" not in map_json or len(map_json["radiations"]) == 0:
                                        self.warn("treatment type Radiation therapy should have one or more radiation submitted")
                                case "Surgery":
                                    if "surgeries" not in map_json or len(map_json["surgeries"]) == 0:
                                        self.warn("treatment type Surgery should have one or more surgery submitted")
                case "treatment_start_date":
                    if map_json["treatment_start_date"] is not None:
                        if "treatment_end_date" in map_json and map_json["treatment_end_date"] is not None:
                            if "dict" in str(type(map_json["treatment_start_date"])):
                                start = map_json["treatment_start_date"]["month_interval"]
                                end = map_json["treatment_end_date"]["month_interval"]
                            else:
                                start = dateparser.parse(map_json["treatment_start_date"]).date()
                                end = dateparser.parse(map_json["treatment_end_date"]).date()
                            if start > end:
                                self.fail("Treatment start cannot be after treatment end.")


    def validate_chemotherapies(self, map_json):
        if "chemotherapy_drug_dose_units" not in map_json or map_json["chemotherapy_drug_dose_units"] is None:
            for x in ["prescribed_cumulative_drug_dose", "actual_cumulative_drug_dose"]:
                if x in map_json and map_json[x] is not None:
                    self.warn(f"chemotherapy_drug_dose_units required if {x} is submitted")


    def validate_hormone_therapies(self, map_json):
        if "hormone_drug_dose_units" not in map_json or map_json["hormone_drug_dose_units"] is None:
            for x in ["prescribed_cumulative_drug_dose", "actual_cumulative_drug_dose"]:
                if x in map_json and map_json[x] is not None:
                    self.warn(f"hormone_drug_dose_units required if {x} is submitted")


    def validate_immunotherapies(self, map_json):
        if "immunotherapy_drug_dose_units" not in map_json or map_json["immunotherapy_drug_dose_units"] is None:
            for x in ["prescribed_cumulative_drug_dose", "actual_cumulative_drug_dose"]:
                if x in map_json and map_json[x] is not None:
                    self.warn(f"immunotherapy_drug_dose_units required if {x} is submitted")


    def validate_radiations(self, map_json):
        # index = self.validation_schema["radiations"]["extra_args"]["index"]
        # if index > 0:
        #     self.fail("Only one radiation is allowed per treatment")

        for prop in map_json:
            match prop:
                case "radiation_boost":
                    if map_json["radiation_boost"]:
                        if "reference_radiation_treatment_id" not in map_json or map_json["reference_radiation_treatment_id"] is None:
                            self.warn("reference_radiation_treatment_id required if radiation_boost = Yes")


    def validate_surgeries(self, map_json):
        specimen_ids = self.validation_schema["primary_diagnoses"]["extra_args"]["specimen_ids"]
        # index = self.validation_schema["surgeries"]["extra_args"]["index"]
        # if index > 0:
        #     self.fail("Only one surgery is allowed per treatment")

        if "submitter_specimen_id" not in map_json:
            if "surgery_site" not in map_json or map_json["surgery_site"] is None:
                self.warn("surgery_site required if submitter_specimen_id not submitted")
            if "surgery_location" not in map_json or map_json["surgery_location"] is None:
                self.warn("surgery_location required if submitter_specimen_id not submitted")
        else:
            if map_json["submitter_specimen_id"] not in specimen_ids:
                self.fail(f"submitter_specimen_id {map_json['submitter_specimen_id']} does not correspond to one of the available specimen_ids {specimen_ids}")


    def validate_comorbidities(self, map_json):
        for prop in map_json:
            match prop:
                case "laterality_of_prior_malignancy":
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
                match prop:
                    case "tobacco_type":
                        if not is_smoker:
                            self.fail(f"tobacco_type cannot be submitted for tobacco_smoking_status = {map_json['tobacco_smoking_status']}")
                    case "pack_years_smoked":
                        if not is_smoker:
                            self.fail(f"pack_years_smoked cannot be submitted for tobacco_smoking_status = {map_json['tobacco_smoking_status']}")


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
