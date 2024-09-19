import os
import sys
# Include src/ directory in the module search path.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(os.sep.join([parent_dir, "src"]))
import clinical_etl.mappings

## Additional mappings customised to my special cohort
def sex(data_value):
    # make sure we only have one value
    mapping_val = mappings.single_val(data_value)

    sex_dict = {
        'Female': 'F',
        'Male': 'M',
    }

    result = None
    for item in sex_dict:
        if (item == data_value) and (mappings.is_null(data_value)) is False:
            result = sex_dict[item]

    return result