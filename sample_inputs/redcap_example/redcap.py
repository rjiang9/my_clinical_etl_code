import mappings
import re


def gender(data_values):
    val = mappings.single_val(data_values)
    if val.lower() == "male":
        return "Man"
    if val.lower() == "female":
        return "Woman"
    return "Non-binary"


def sex_at_birth(data_values):
    val = mappings.single_val(data_values)
    return val


def comorbidity_type_code(data_values):
    val = mappings.single_val(data_values)
    code_lookup = {
        "malignant neoplasm of descended testis": "C62.11"
    }
    if val is not None and val.lower() in code_lookup:
        return code_lookup[val.lower()]
    return None


def method_of_progression_status(data_values):
    val = mappings.single_val(data_values)
    if val is not None:
        vals = val.split('|')

    for i in range(0, len(vals)):
        if vals[i] == "Anatomic pathology (procedure)":
            vals[i] = "Histopathology test (procedure)"
    return vals


def submitter_specimen_id(data_values):
    val = mappings.single_val(data_values)
    if val is not None:
        return f"specimen_{val}"


def io_identifier(data_values):
    val = mappings.single_val(data_values)
    if val is not None:
        #pembrolizumab 25 MG/ML [Keytruda]
        io_match = re.match(r"(.+?) (\d+?) (.+?) \[(.+?)\]", val)
        if io_match is not None:
            return io_match.group(4)
    return None


def io_prescribed_dose(data_values):
    val = mappings.single_val(data_values)
    if val is not None:
        #pembrolizumab 25 MG/ML [Keytruda]
        io_match = re.match(r"(.+?) (\d+?) (.+?) \[(.+?)\]", val)
        if io_match is not None:
            return int(io_match.group(2))
    return None


def treatment_index(data_values):
    treatment_ids = []
    for i in range(0, len(data_values['submitter_donor_id']['Treatment'])):
        treatment_ids.append(submitter_treatment_id(data_values, i))

    result = []
    comp_key = list(data_values.keys())[-1]
    if len(data_values[comp_key][list(data_values[comp_key].keys())[0]]) > 0:
        comparison = data_values[comp_key][list(data_values[comp_key].keys())[0]][0]
    else:
        comparison = ""
    for treatment_id in treatment_ids:
        if comparison == treatment_id:
            result.append(comparison)
        else:
            result.append(None)
    return {
        "field": "submitter_treatment_id",
        "sheet": "Treatment",
        "values": result
    }


def submitter_treatment_id(data_values, i=0):
    if 'list' in str(type(data_values['submitter_donor_id']['Treatment'])):
        donor_id = data_values['submitter_donor_id']['Treatment'][i]
        treatment_id = data_values['Treatment_id']['Treatment'][i]
        treatment_type = data_values['treatment_type']['Treatment'][i]
    else:
        donor_id = data_values['submitter_donor_id']['Treatment']
        treatment_id = data_values['Treatment_id']['Treatment']
        treatment_type = data_values['treatment_type']['Treatment']

    pd_id = data_values['submitter_primary_diagnosis_id']['Primary Diagnosis'][0]
    return f"{donor_id}-{pd_id}-{treatment_type}-{treatment_id}"


def radiation_therapy_modality(data_values):
    val = mappings.single_val(data_values)

    lookup = {
        "Photons": "Megavoltage radiation therapy using photons (procedure)"
        # Teleradiotherapy using electrons (procedure)
        # Teleradiotherapy protons (procedure)
        # Teleradiotherapy neutrons (procedure)
        # Brachytherapy (procedure)
        # Radiopharmaceutical
        # Other"
    }

    if val is not None and val in lookup:
        return lookup[val]
    return None


def anatomical_site_irradiated(data_values):
    val = mappings.single_val(data_values)

    lookup = {
        "Oropharyngeal structure (body structure)": "Oropharynx",
        "Bladder part (body structure)": "Bladder"
    }

    if val is not None and val in lookup:
        return lookup[val]
    return None


def surgery_site(data_values):
    val = mappings.pipe_delim(data_values)
    if len(val) > 0:
        return val[0]
    return None


def surgery_type(data_values):
    val = mappings.single_val(data_values)

    lookup = {
        "Debulking": "Tumor Debulking"
    }

    if val is not None and val in lookup:
        return lookup[val]
    return None


def surgery_location(data_values):
    val = mappings.single_val(data_values)

    lookup = {
        "Primary site": "Primary"
    }

    if val is not None and val in lookup:
        return lookup[val]
    return None


def residual_tumour_classification(data_values):
    val = mappings.single_val(data_values)

    lookup = {
        "R0 (no residual tumour)": "R0"
    }

    if val is not None and val in lookup:
        return lookup[val]
    return None


def margin_types_involved(data_values):
    val = mappings.single_val(data_values)
    vals = val.split("|")

    lookup = {
        "None": "Not applicable"
    }
    result = []
    for val in vals:
        if val in lookup:
            result.append(lookup[val])
    return result


def response_to_treatment(data_values):
    return "Physician assessed partial response"


def treatment_setting(data_values):
    val = mappings.single_val(data_values)
    if val == "Not applicable":
        return "Adjuvant"
    return val