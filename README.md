# clinical_ETL_code

This repository provides tools to convert input csv files with clinical (phenotypic) data into a json aligned with a provided openapi schema. You can provide custom mapping functions to transform data in your input file before writing to the json.

Specifically, this code was designed to convert clinical data for the MOHCCN project into the packet format needed for ingest into CanDIG's clinical data service (katsu).

## Using clinical_etl as a package
You can import this module as a package by including the following in your `requirements.txt`:
```
clinical_etl@git+https://github.com/CanDIG/clinical_ETL_code.git@stable
```
If you need the latest version, you can replace `stable` with `develop`.

## CSVConvert
Most of the heavy lifting is done in the [`CSVConvert.py`](CSVConvert.py) script. See sections below for setting up the inputs and running the script.

This script:
* reads a file (`.xlsx` or `.csv`) or a directory of files (`.csv`)
* reads a [template file](#mapping-template) that contains a list of fields and (if needed) a mapping function
* for each field for each patient, applies the mapping function to transform the raw data into permissible values against the provided schema
* exports the data into a json file(s) appropriate for ingest
* performs Validation and gives warning and error feedback for any data that does not meet the schema requirements

### Environment set-up & Installation
Prerequisites:
- [Python 3.10+](https://www.python.org/)
- [pip](https://github.com/pypa/pip/)

Set up and activate a [virtual environment](https://docs.python.org/3/tutorial/venv.html) using the python environment tool of your choice. For example using `venv` on linux/macOS systems
```commandline
python -m venv /path/to/new/virtual/environment
source /path/to/new/virtual/environment/bin/activate
```

[See here for Windows instructions](https://realpython.com/python-virtual-environments-a-primer/)

Clone this repo and enter the repo directory
```commandline
git clone https://github.com/CanDIG/clinical_ETL_code.git
cd clinical_ETL_code
```

Install the repo's requirements in your virtual environment
```commandline
pip install -r requirements.txt
```

>[!NOTE]
> If Python can't find the `clinical_etl` module when running `CSVConvert`, install the depencency manually:
> ```
> pip install -e clinical_ETL_code/
> ```

Before running the script, you will need to have your input files, this will be clinical data in a tabular format (`xlsx`/`csv`) that can be read into program and a cohort directory containing the files that define the schema and mapping configurations.

### Input file/s format

The input for `CSVConvert` is either a single xlsx file, a single csv, or a directory of csvs that contain your clinical data. If providing a spreadsheet, there can be multiple sheets (usually one for each sub-schema). Examples of how csvs may look can be found in [tests/raw_data](tests/raw_data).

All rows must contain identifiers that allow linkage between the objects in the schema, for example, a row that describes a Treatment must have a link to the Donor / Patient id for that Treatment.

Data should be [tidy](https://r4ds.had.co.nz/tidy-data.html), with each variable in a separate column, each row representing an observation, and a single data entry in each cell. In the case of fields that can accept an array of values, the values within a cell should be delimited such that a mapping function can accurately return an array of permissible values.

If you are working with exports from RedCap, the sample files in the [`sample_inputs/redcap_example`](sample_inputs/redcap_example) folder may be helpful. 

### Setting up a cohort directory

For each dataset (cohort) that you want to convert, create a directory outside of this repository. For CanDIG devs, this will be in the private `data` repository. This cohort directory should contain the same files as shown in the [`sample_inputs/generic_example`](sample_inputs/generic_example) directory, which are:

* a [`manifest.yml`](#Manifest-file) file with configuration settings for the mapping and schema validation
* a [mapping template](#Mapping-template) csv that lists custom mappings for each field (based on `moh_template.csv`)
* (if needed) One or more python files that implement any cohort-specific mapping functions (See [mapping functions](mapping_functions.md) for detailed information)

Example files for how to convert a large single csv export, such as those exported from a redcap database can be found in [`sample_inputs/redcap_example`](sample_inputs/redcap_example).

> [!IMPORTANT]
> If you are placing this directory under version control and the cohort is not sample / synthetic data, do not place raw or processed data files in this directory, to avoid any possibility of committing protected data.

#### Manifest file
The `manifest.yml` file contains settings for the cohort mapping. There is a sample file in [`sample_inputs/generic_example/manifest.yml`](sample_inputs/generic_example/manifest.yml) with documentation and example inputs. The fields are:

| field         | description                                                                                                                                                                                               |
|---------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| description   | A brief description of what mapping task this manifest is being used for                                                                                                                                  |
| mapping       | the mapping template csv file that lists the mappings for each field based on `moh_template.csv`, assumed to be in the same directory as the `manifest.yml` file                                          |
| identifier    | the unique identifier for the donor or root node                                                                                                                                                          |
| schema        | a URL to the openapi schema file                                                                                                                                                                          |
| schema_class  | The name of the class in the schema used as the model for creating the map.json. Currently supported: `MoHSchemaV2` and `MoHSchemaV3` - for clinical MoH data and `GenomicSchema` for creating a genomic ingest linking file. |
| reference_date | a reference date used to calculate date intervals, formatted as a mapping entry for the mapping template                                                                                                 |
| date_format | Specify the format of the dates in your input data. Use any combination of the characters `DMY`to specify the order (e.g. `DMY`, `MDY`, `YMD`, etc).                                                                                    |
| functions     | A list of one or more filenames containing additional mapping functions, can be omitted if not needed. Assumed to be in the same directory as the `manifest.yml` file                                     |

#### Mapping template

You'll need to create a mapping template that defines the mapping between the fields in your input files and the fields in the target schema. It also defines what mapping functions (if any) should be used  to transform the input data into the required format to pass validation under the target schema.

Each line in the mapping template is composed of comma separated values with two components. The first value is an `element` or field from the target schema and the second value contains a suggested `mapping method` or function to map a field from an input sheet to a valid value for the identified `element`. Each `element`, shows the full object linking path to each field required by the model. These values should not be edited.

If you are generating a mapping for the current CanDIG MoH model, you can use the pre-generated [`moh_template.csv`](moh_template.csv) file. This file is modified from the auto-generated template to update a few fields that require specific handling.

You will need to edit the `mapping method` values in each line in the following ways:
1. Replace the generic sheet names (e.g. `DONOR_SHEET`, `SAMPLE_REGISTRATIONS_SHEET`) with the sheet/csv names you are using as your input to `CSVConvert.py`
2. Replace suggested field names with the relevant field/column names in your input sheets/csvs, if they differ

If the field does not map in the same way as the suggested mapping function you will also need to:

3. Choose a different existing [mapping function](src/clinical_etl/mappings.py) or write a new function that does the required transformation and save it in a python file that is specified in your `manifest.yml` in the `functions` section. Functions in your custom mapping _must_ be fully referenced by their module name, e.g. `sample_custom_mappings.sex()`. (See the [mapping instructions](mapping_functions.md) for detailed documentation on writing your own mapping functions.)

>[!NOTE]
> * Do not edit, delete, or re-order the template lines, except to adjust the sheet name, mapping function and field name in the `mapping method` column.
> * Fields not requiring mapping can be commented out with a # at the start of the line

<details>
<summary>Generating a template from a different schema</summary>
The `generate_schema.py` script will generate a template file based an openapi.yaml file.

```
$ python src/clinical_etl/generate_schema.py -h
usage: generate_schema.py [-h] --url URL [--out OUT]

options:
  -h, --help  show this help message and exit
  --url URL   URL to openAPI schema file (raw github link)
  --schema    Name of schema class. Default is MoHSchemaV3
  --out OUT   name of output file; csv extension will be added. Default is template
```
</details>

### Running `CSVConvert` from the command line

CSVConvert requires two inputs:
1. a path to a multi-sheet spreadsheet or path to csvs specified with [`--input`](#Input-file/s-format)
2. a path to a `manifest.yml`, in a directory that also contains the other files defined in [Setting up a cohort directory](#Setting-up-a-cohort-directory)

```
python src/clinical_etl/CSVConvert.py -h
usage: CSVConvert.py [-h] --input INPUT --manifest MANIFEST [--test] [--verbose] [--index] [--minify]

options:
  -h, --help           show this help message and exit
  --input INPUT        Path to either an xlsx file or a directory of csv files for ingest
  --manifest MANIFEST  Path to a manifest file describing the mapping. See README for more information
  --test               Use exact template specified in manifest: do not remove extra lines
  --verbose, --v       Print extra information, useful for debugging and understanding how the code runs.
  --index, --i         Output 'indexed' file, useful for debugging and seeing relationships.
  --minify             Remove white space and line breaks from json outputs to reduce file size. Less readable for humans.
```

* `--test` allows you to add extra lines to your manifest's template file that will be populated in the mapped schema. NOTE: this mapped schema will likely not be a valid mohpacket: it should be used only for debugging.

Example usage:

```
python src/clinical_etl/CSVConvert.py --input test_data/raw_data --manifest test_data/manifest.yml
```

The main output `<INPUT_DIR>_map.json` and optional output`<INPUT_DIR>_indexed.json` will be in the parent of the `INPUT` directory / file. In the example above, this would be in the `test_data` directory.

Validation will automatically be run after the conversion is complete. Any validation errors or warnings will be reported both on the command line and as part of the `<INPUT_DIR>_map.json` file.

>[!NOTE]
> If Python can't find the `clinical_etl` module when running `CSVConvert`, install the depencency manually:
> ```
> pip install -e clinical_ETL_code/
> ```

#### Format of the output files

`<INPUT_DIR>_map.json` is the main output and contains the results of the mapping, conversion and validation as well as summary statistics.

A summarised example of the output is below:

```json
{
    "openapi_url": "https://raw.githubusercontent.com/CanDIG/katsu/develop/chord_metadata_service/mohpackets/docs/schema.yml",
    "katsu_sha": < git sha of the katsu version used for the schema >,
    "donors": < An array of JSON objects, each one representing a DonorWithClinicalData in katsu >,
    "statistics": {
        "required_but_missing": {
            < for each schema in the model, a list of required fields and how many cases are missing this value (out of the total number of occurrences) >
            "donors": {
              "submitter_donor_id": {
                  "total": 6,
                  "missing": 0
              }
        },
        "schemas_used": [
            "donors"
        ],
        "cases_missing_data": [
            "DONOR_5"
        ],
        "schemas_not_used": [
            "exposures",
            "biomarkers"
        ],
        "summary_cases": {
            "complete_cases": 13,
            "total_cases": 14
        }
    }
}
```

The mapping and transformation result is found in the `"donors"` key.

Arrays of validation warnings and errors are found in `validation_warnings` & `validation_errors`.

Summary statistics about the completeness of the objects against the schema are in the `statistics` key. You can create a readable CSV table
of the summary statistics by running `completeness_table.py`. The table will be saved in `<INPUT_DIR>_completeness.csv`.
```
python src/clinical_etl/completeness_table.py --input <INPUT_DIR>_map.json
```

`<INPUT_DIR>_validation_results.json` contains all validation warnings and errors.

`<INPUT_DIR>_indexed.json` contains information about how the ETL is looking up the mappings and can be useful for debugging. It is only generated if the `--index` argument is specified when CSVConvert is run. Note: This file can be very large if the input data is large.

## Testing

Continuous integration testing for this repository is implemented through Pytest and GitHub Actions which run when pushes occur. Build results can be found at [this repository's GitHub Actions page](https://github.com/CanDIG/clinical_ETL_code/actions/workflows/test.yml).

To run tests manually, enter from command line `$ pytest`

### When tests fail...

<details>
<summary>"Compare moh_template.csv" fails</summary>

### You changed the `moh_template.csv` file:

To fix this, you'll need to update the diffs file. Run `bash update_moh_template.sh` and commit the changes that are generated for `test_data/moh_diffs.txt`.

### You did not change the `moh_template.csv` file:

There have probably been MoH model changes in katsu.

Run the `update_moh_template.sh` script to see what's changed in `test_data/moh_diffs.txt`. Update `moh_template.csv` to reconcile any differences, then re-run `update_moh_template.sh`. Commit any changes in both `moh_template.csv` and `test_data/moh_diffs.txt`.
</details>

## Validating the mapping

You can validate the generated json mapping file against the MoH data model. The validation will compare the mapping to the json schema used to generate the template, as well as other known requirements and data conditions specified in the MoH data model.

```
$ python src/clinical_etl/validate_coverage.py -h
usage: validate_coverage.py [-h] --json JSON [--verbose]

options:
  -h, --help      show this help message and exit
  --json JSON     <input-file-path-name>_map.json file generated by CSVConvert.py.
  --verbose, --v  Print extra information
```

The output will report errors and warnings separately. JSON schema validation failures and other data mismatches will be listed as errors, while fields that are conditionally required as part of the MoH model but are missing will be reported as warnings.

<!-- # NOTE: the following sections have not been updated for current versions.

## Creating a dummy json file for testing
You can use an mohcode template file (created as described above) alone to create a dummy ingest file without actual data.

`python create_test_mapping.py` creates a JSON that is filled in (without using mapping functions) with placeholder or dummy values. You can specify the placeholder value with the argument `--placeholder`. If no template file is specified with `--template`, the current MCODE_SCHEMA of katsu is used and the JSON is outputted to stdout. Otherwise, the file is saved to `<template>_testmap.json`.

This JSON file can be ingested into katsu and compared with the ingested value using https://github.com/CanDIG/candigv2-ingest/blob/main/katsu_validate_dataset.py.

## Quantifying coverage for datasets and mappings
The `quantify_coverage.py` tool takes the same arguments as `CSVConvert.py`:
```
$ python CSVConvert.py [-h] [--input INPUT] [--mapping|manifest MAPPING]

--input: path to dataset

--mapping or --manifest: Path to a manifest file describing the mapping
```

This tool outputs information quantifying:
* how much of the schema is covered by the mapping
* how much of the dataset is covered by the mapping -->
