# Mapping functions

## Mapping template format

Each line in the mapping template represents one field in the schema.
For example, `date_of_diagnosis` is part of the `primary_diagnoses` schema within a `DONOR`:

`DONOR.INDEX.primary_diagnoses.INDEX.date_of_diagnosis,`

The `INDEX` after the field name indicates that there can be multiple instances. For example, this line indicates there can be one or more primary diagnoses per DONOR, each with one or more specimens:

`DONOR.INDEX.primary_diagnoses.INDEX.specimens.INDEX.tumour_grade,`

Entries that begin with `##` are informational.

## Defining mapping functions

For each field, decide:

1. What column name in my input file(s) goes with this field?
2. Does the data need to be transformed to align with the expectations of the schema?
    a. If so, can I use a generic mapping function, or do I need to write my own?

The template suggests a default mapping, of the format `{mapping_function(DATA_SHEET.column_name)}`. If your data does not align with this, you may have to change this.

### Aligning field names

Sometimes your raw data contains column headings that do not exactly match the schema fields. For example, if your input file uses "Birthdate" instead of "date_of_birth", you may need to change the default mapping:

`DONOR.INDEX.date_of_birth, {single_val(DONOR_SHEET.Birthdate)}`

### Specifying index fields

For cases where there can be multiple instances of a schema (e.g. multiple treatments, or specimens), you _must_ specify an indexing field for that schema. In the template, this looks like a line ending in `INDEX` with the `indexed_on` mapping function:

```
DONOR.INDEX.primary_diagnoses.INDEX, {indexed_on(PRIMARY_DIAGNOSES_SHEET.submitter_donor_id)}
DONOR.INDEX.primary_diagnoses.INDEX.submitter_primary_diagnosis_id, {single_val(PRIMARY_DIAGNOSES_SHEET.submitter_primary_diagnosis_id)}
DONOR.INDEX.primary_diagnoses.INDEX.date_of_diagnosis, {single_date(PRIMARY_DIAGNOSES_SHEET.date_of_diagnosis)}
```

Here, `primary_diagnoses` will be added as an array for the Donor with `submitter_donor_id`. Each entry in `primary_diagnoses` will use the values on the `PRIMARY_DIAGNOSES_SHEET` that have the same `submitter_donor_id`.

If your schema doesn't contain any instances of a particular indexed field, you can specify `NONE`:
`{indexed_on(NONE)}`

If your schema requires more complex mapping calculations, you can define an index function in your mapping file. The result of this index function should have the same shape as mappings.indexed_on:
```
{
  "sheet": sheet,
  "field": field,
  "values": [array of calculated values to use on the sheet.field]
}
```


## Transforming data using standard functions

In addition to mapping column names, you can also transform the values inside the cells to make them align with the schema. We've already seen the simplest case - the `single_val` function takes a single value for the named field and returns it (and should only be used when you expect one single value).

The standard functions are defined in `mappings.py`. They include functions for handling single values, list values, dates, and booleans.

Many functions take one or more `data_values` arguments as input. These are a dictionary representing how the CSVConvert script parses each cell of the input data. It is a dictionary of the format `{<field>:{<OBJECT_SHEET>: <value>}}`, e.g. `{'date_of_birth': {'Donor': '6 Jan 1954'}}`.

A detailed index of all standard functions can be viewed below in the [Standard functions index](#Standard-functions-index).

### Dealing with Dates

As of version 2.1 of the [MoHCCN Data Model](https://www.marathonofhopecancercentres.ca/docs/default-source/policies-and-guidelines/clinical-data-model-v2.1/mohccn-clinical-data-model-release-notes_sep2023.pdf?Status=Master&sfvrsn=19ece028_3), dates need to be converted into date intervals relative to the earliest date of diagnosis. Support for this has been incorporated into clinical_ETL_code v.2.0.0. In order to convert dates to date intervals, a `reference_date` must be provided in the `manifest.yml`, which should be the patient's first date of diagnosis. You can assign the first date of diagnosis with:
```commandline
reference_date: earliest_date(Donor.date_resolution, PrimaryDiagnosis.date_of_diagnosis)
```

In the mapping csv, the in-built `date_interval()mapping function can be used to calculate the appropriate date interval information for any date-type field. e.g.:

```commandline
DONOR.INDEX.date_of_birth, {date_interval(Donor.date_of_birth)}
```

To avoid issues with ambiguous dates, ensure all the dates in your input date are in the same format, then specify that `date_format` in the manifest file so the day, month, and year are parsed correctly. The format can be any combination of the characters `DMY`to specify the order (e.g. `DMY`, `MDY`, `YMD`, etc).



If input data has pre-calculated date intervals as integers, the `int_to_date_interval_json()` function can be used to transform the integer into the required DateInterval json object. e.g.:

```commandline
DONOR.INDEX.date_of_death, {int_to_date_interval_json(Donor.date_of_death)}
```

## Writing your own custom functions

If the data cannot be transformed with one of the standard functions, you can define your own. In your data directory (the one that contains `manifest.yml`) create a python file (let's assume you called it `new_cohort.py`) and add the name of that file as the `functions` entry in the manifest (without the .py extension).

In your data directory (the one that contains `manifest.yml`) create a python file (let's assume you called it `new_cohort.py`) and add the name of that file as a .yml list after `functions` in the manifest.  For example:
```
functions:
  - new_cohort
```

Following the format in the generic `mappings.py`, write your own functions in your python file to translate the data.

To use a custom mapping function in the template, you must specify the file and function using dot-separated notation:

DONOR.INDEX.primary_diagnoses.INDEX.basis_of_diagnosis,{**new_cohort.custom_function**(DATA_SHEET.field_name)}

Examples:

Map input values to output values (in case your data capture used different values than the model):

```
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
```

You can explicitly create a dictionary based on multiple raw data values and have the mapping method's return value overwrite the rest of the entries in the dictionary:

```
##prop_a,
prop_a.prop_b, {my_mapping_func(dataval_c, dataval_d)}

with

def my_mapping_func(data_values) {
  return {
    "prop_c": "FOO_" + mappings.single_val(data_values['dataval_c']),
    "prop_d": "BAR_" + mappings.single_val(data_values['dataval_d']),
  }
}

represents the following JSON dict:
{
  "prop_a": {
      "prop_b":
        {
          "prop_c": "FOO_dataval_c",
          "prop_d": "BAR_dataval_d"
        }
    }
}

```

# Standard Functions Index

<!--- documentation below this line is generated automatically by running generate_mapping_docs.py --->

Module mappings
===============

Functions
---------

    
`boolean(data_values)`
:   Convert value to boolean.
    
    Args:
        data_values: A string to be converted to a boolean
    
    Returns:
        A boolean based on the input,
        `False` if value is in ["No", "no", "N", "n", "False", "false", "F", "f"]
        `True` if value is in ["Yes", "yes", "Y", "y", True", "true", "T", "t"]
        None if value is in [`None`, "nan", "NaN", "NAN"]
        None otherwise

    
`concat_vals(data_values)`
:   Concatenate several data values
    
    Args:
        data_values: a values dict with a list of values
    
    Returns:
        A concatenated string

    
`date(data_values)`
:   Format a list of dates to ISO standard YYYY-MM
    
    Parses a list of strings representing dates into a list of strings with dates in ISO format YYYY-MM.
    
    Args:
        data_values: a value dict with a list of date-like strings
    
    Returns:
        a list of dates in YYYY-MM format or None if blank/empty/unparseable

    
`date_interval(data_values)`
:   Calculates a date interval from a given date relative to the reference date specified in the manifest.
    
    Args:
        data_values: a values dict with a date
    
    Returns:
        A dictionary with calculated month_interval and optionally a day_interval depending on the specified
        date_resolution.

    
`earliest_date(data_values)`
:   Calculates the earliest date from a set of dates
    
    Args:
        data_values: A values dict of dates of diagnosis and date_resolution
    
    Returns:
        A dictionary containing the earliest date (`offset`) as a date object and the provided `date_resolution`

    
`flat_list_val(data_values)`
:   Take a list mapping and break up any stringified lists into multiple values in the list.
    
    Attempts to use ast.literal_eval() to parse the list, uses split(',') if this fails.
    
    Args:
        data_values: a values dict with a stringified list, e.g. "['a','b','c']"
    Returns:
        A parsed list of items in the list, e.g. ['a', 'b', 'c']


`floating(data_values)`

:   Convert a value to a float.
    
    Args:
        data_values: A values dict
    
    Returns:
        A values dict with a string or integer converted to a float or None if null value
    
    Raises:
        ValueError by float() if it cannot convert to float.

    
`has_value(data_values)`
:   Returns a boolean based on whether the key in the mapping has a value.

    
`index_val(data_values)`
:   Take a mapping with possibly multiple values from multiple sheets and return an array.

    
`indexed_on(data_values)`
:   Default indexing value for arrays.
    
    Args:
        data_values: a values dict of identifiers to be indexed
    
    Returns:
        a dict of the format:
        {"field": <identifier_field>,"sheet_name": <sheet_name>,"values": [<identifiers>]}

    
`int_to_date_interval_json(data_values)`
:   Converts an integer date interval into JSON format.
    
    Args:
        data_values: a values dict with an integer.
    
    Returns:
        A dictionary with a calculated month_interval and optionally a day_interval depending on the specified date_resolution in the donor file.

    
`integer(data_values)`
:   Convert a value to an integer.
    
    Args:
        data_values: a values dict with value to be converted to an int
    Returns:
        an integer version of the input value
    Raises:
        ValueError if int() cannot convert the input

    
`list_val(data_values)`
:   Takes a mapping with possibly multiple values from multiple sheets and returns an array of values.
    
    Args:
        data_values: a values dict with a list of values
    Returns:
        The list of values

    
`moh_indexed_on_donor_if_others_absent(data_values)`
:   Maps an object to a donor if not otherwise linked.
    
    Specifically for the FollowUp object which can be linked to multiple objects.
    
    Args:
        **data_values: any number of values dicts with lists of identifiers, NOTE: values dict with donor identifiers
        must be specified first.
    
    Returns:
        a dict of the format:
    
            {'field': <field>, 'sheet': <sheet>, 'values': [<identifier or None>, <identifier or None>...]}
    
        Where the 'values' list contains a donor identifier if it should be linked to that donor or None if already
        linked to another object.

    
`ontology_placeholder(data_values)`
:   Placeholder function to make a fake ontology entry.
    
    Should only be used for testing.
    
    Args:
        data_values: a values dict with a string value representing an ontology label
    
    Returns:
        a dict of the format:
        {"id": "placeholder","label": data_values}

    
`pipe_delim(data_values)`
:   Takes a string and splits it into an array based on a pipe delimiter.
    
    Args:
         data_values: values dict with single pipe-delimited string, e.g. "a|b|c"
    
    Returns:
        a list of strings split by pipe, e.g. ["a","b","c"]

    
`placeholder(data_values)`
:   Return a dict with a placeholder key.

    
`single_date(data_values)`
:   Parses a single date to YYYY-MM format.
    
    Args:
        data_values: a value dict with a date
    
    Returns:
        a string of the format YYYY-MM, or None if blank/unparseable

    
`single_val(data_values)`
:   Parse a values dict and return the input as a single value.
    
    Args:
        data_values: a dict with values to be squashed
    
    Returns:
        A single value with any null values removed
        None if list is empty or contains only 'nan', 'NaN', 'NAN'
    
    Raises:
        MappingError if multiple values found

Classes
-------

`MappingError(value)`
:   Common base class for all non-exit exceptions.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException
