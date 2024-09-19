import pytest
import yaml
import os
import sys
import json
# Include src/clinical_etl directory in the module search path.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(os.sep.join([parent_dir, "src"]))
from clinical_etl import CSVConvert
from clinical_etl import mappings
from clinical_etl.mohschemav3 import MoHSchemaV3

# read sheet from given data pathway
REPO_DIR = os.path.abspath(f"{os.path.dirname(os.path.realpath(__file__))}")

@pytest.fixture
def schema():
    manifest_file = f"{REPO_DIR}/manifest.yml"
    with open(manifest_file, 'r') as f:
        manifest = yaml.safe_load(f)
    if manifest is not None:
        return MoHSchemaV3(manifest['schema'])
    return None


@pytest.fixture
def packets():
    input_path = f"{REPO_DIR}/raw_data"
    manifest_file = f"{REPO_DIR}/manifest.yml"
    mappings.INDEX_STACK = []
    return_values = CSVConvert.csv_convert(input_path, manifest_file, verbose=False)
    return return_values[0]


def test_csv_convert(packets):
    # there are 6 donors
    assert len(packets) == 6


def test_external_mapping(packets):
    assert packets[0]['test_mapping'] == "test string"


def test_donor_1(packets):
    for packet in packets:
        if packet['submitter_donor_id'] == "DONOR_1":
            # test Followups: FOLLOW_UP_2 is in TR_1, FOLLOW_UP_1 is in PD_1, FOLLOW_UP_3 and FOLLOW_UP_4 are in DONOR_1
            for pd in packet['primary_diagnoses']:
                if "followups" in pd:
                    for f in pd['followups']:
                        # assert f['submitter_primary_diagnosis_id'] == pd['submitter_primary_diagnosis_id']
                        assert f['submitter_follow_up_id'] == "FOLLOW_UP_1"
                if "treatments" in pd:
                    for t in pd["treatments"]:
                        if "followups" in t:
                            for f in t['followups']:
                                # assert f['submitter_treatment_id'] == t['submitter_treatment_id']
                                assert f['submitter_follow_up_id'] == "FOLLOW_UP_2"
            if "followups" in packet:
                assert len(packet['followups']) == 2
                for f in packet['followups']:
                    assert f['submitter_follow_up_id'] in ["FOLLOW_UP_3", "FOLLOW_UP_4"]
        else:
            continue


def test_donor_2(packets):
    for packet in packets:
        if packet['submitter_donor_id'] == "DONOR_2":
            # DONOR_2 has two primary diagnoses, PD_2 and PD_2_1
            assert len(packet['primary_diagnoses']) == 2
            for pd in packet['primary_diagnoses']:
                assert 'specimens' in pd
                for specimen in pd['specimens']:
                    assert specimen['submitter_specimen_id'] in ["SPECIMEN_5", "SPECIMEN_4", "SPECIMEN_7"]
                    if 'sample_registrations' in specimen:
                        for sample in specimen['sample_registrations']:
                            assert sample["submitter_sample_id"] in ["SAMPLE_REGISTRATION_3", "SAMPLE_REGISTRATION_1", "SAMPLE_REGISTRATION_2"]
        else:
            continue


def test_validation(packets, schema):
    schema.validate_ingest_map({"donors": packets})
    print(schema.validation_warnings)
    assert len(schema.validation_warnings) == 4
    # should be the following 4 warnings:
    # "DONOR_5: cause_of_death required if is_deceased = Yes",
    # "DONOR_5: date_of_death required if is_deceased = Yes",
    # "DONOR_5 > PD_5: clinical_stage_group is required for clinical_tumour_staging_system Revised International staging system (RISS)",
    # "DONOR_5 > PD_5 > TR_10: treatment type Systemic therapy should have one or more systemic therapies submitted"

    print(schema.validation_errors)

    # temporary: remove 'month_interval' errors:
    non_interval_errors = []
    for e in schema.validation_errors:
        if "month_interval" not in e:
            non_interval_errors.append(e)
    schema.validation_errors = non_interval_errors

    assert len(schema.validation_errors) == 11
    # should be the following 11 errors:
    # "DONOR_2 > PD_2 > TR_2: Treatment start cannot be after treatment end.",
    # "DONOR_2 > PD_2 > TR_2: Systemic therapy end date cannot be after its treatment end date.",
    # "DONOR_2 > PD_2 > TR_2: Systemic therapy start date cannot be earlier than its treatment start date.",
    # "DONOR_2 > PD_2 > TR_2: Systemic therapy end date cannot be after its treatment end date.",
    # "DONOR_2 > PD_2_1 > TR_8: Systemic therapy end date cannot be after its treatment end date.",
    # "DONOR_3 > DUPLICATE_ID > primary_site: 'Tongue' is not valid under any of the given schemas",
    # "DONOR_3 > PD_3 > TR_3: Systemic therapy start date cannot be earlier than its treatment start date.",
    # "DONOR_1: PD_1 > TR_1: date_of_death cannot be earlier than treatment_end_date ",
    # "DONOR_1: PD_1 > TR_1: treatment_start_date cannot be after date_of_death ",
    # "DONOR_5: lost_to_followup_after_clinical_event_identifier cannot be present if is_deceased = Yes",
    # "Duplicated IDs: in schema followups, FOLLOW_UP_4 occurs 2 times"

    # there should be an item named DUPLICATE_ID in both followup and sample_registration
    print(json.dumps(schema.identifiers, indent=2))
    assert schema.identifiers["followups"]["DUPLICATE_ID"] == 1
    assert schema.identifiers["primary_diagnoses"]["DUPLICATE_ID"] == 1


# test mapping that uses values from multiple sheets:
def test_multisheet_mapping(packets):
    for packet in packets:
        for pd in packet["primary_diagnoses"]:
            if "specimens" in pd:
                for s in pd["specimens"]:
                    assert "multisheet" in s
                    assert "placeholder" in s["multisheet"]
                    if s["submitter_specimen_id"] == "SPECIMEN_5":
                        assert s["multisheet"]["placeholder"]["submitter_specimen_id"]["Specimen"] == "SPECIMEN_5"
                        assert len(s["multisheet"]["placeholder"]["submitter_specimen_id"]["Sample_Registration"]) == 3
                        assert len(s["multisheet"]["placeholder"]["extra"]["Sample_Registration"]) == 3
                    if s["submitter_specimen_id"] == "SPECIMEN_6":
                        assert s["multisheet"]["placeholder"]["submitter_specimen_id"]["Specimen"] == "SPECIMEN_6"
                        assert len(s["multisheet"]["placeholder"]["submitter_specimen_id"]["Sample_Registration"]) == 1
                        assert len(s["multisheet"]["placeholder"]["extra"]["Sample_Registration"]) == 1
                    if s["submitter_specimen_id"] == "SPECIMEN_3":
                        assert s["multisheet"]["placeholder"]["submitter_specimen_id"]["Specimen"] == "SPECIMEN_3"
                        assert len(s["multisheet"]["placeholder"]["submitter_specimen_id"]["Sample_Registration"]) == 0
                        assert len(s["multisheet"]["placeholder"]["extra"]["Sample_Registration"]) == 0

