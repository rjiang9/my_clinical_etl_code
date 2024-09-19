import json
import dateparser
from clinical_etl.schema import BaseSchema, ValidationError


"""
A class for the representation of a GenomicSample object for candigv2-ingest.
"""

class GenomicSchema(BaseSchema):
    schema_name = "GenomicSample"
    base_name = "GENOMIC_ID"


    ## Following are specific checks for required fields in the MoH data model, as well as checks for conditionals specified in the model.
    validation_schema = {
        "genomic_ids": {
            "id": "genomic_file_id",
            "name": "Genomic File ID",
            "required_fields": [],
            "nested_schemas": [
                "samples"
            ]
        },
        "samples": {
            "id": "submitter_sample_id",
            "name": "Submitter Sample Pairing",
            "required_fields": [
                "genomic_file_sample_id"
            ],
            "nested_schemas": []
        }
    }


    def validate_genomic_ids(self, map_json):
        return


    def validate_samples(self, map_json):
        return
