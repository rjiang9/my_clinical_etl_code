# mappings and validation based on the mohccn schema

import requests
import yaml
import json
import re
from copy import deepcopy
import jsonschema
from collections import Counter
import openapi_spec_validator as osv


class ValidationError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(f"Validation error: {self.value}")

"""
Convenience methods for validating openapi as jsonschema
"""

def openapi_to_jsonschema(schema_text, schema_name):
    # save off all the component schemas into a "defs" component that can be passed into a jsonschema validation
    defs_set = set()
    schema_text = schema_text.split("\n")
    for i in range(0, len(schema_text)):
        ref_match = re.match(r"(.*\$ref:).*(#/components/schemas/.+)$", schema_text[i])
        if ref_match is not None:
            schema_text[i] = schema_text[i].replace("#/components/schemas/", "#/$defs/")
            defs_set.add(ref_match.group(2).strip('\"').strip("\'").replace("#/components/schemas/", ""))

    openapi_components = yaml.safe_load("\n".join(schema_text))["components"]["schemas"]
    # populate defs for jsonschema
    defs = {}
    for d in defs_set:
        defs[d] = openapi_components[d]

    json_schema = deepcopy(openapi_components[schema_name])
    json_schema["$defs"] = defs
    return json_schema

"""
Base class to represent a Katsu OpenAPI schema for ETL.
"""

class BaseSchema:
    # The component name in the OpenAPI specification
    schema_name = None

    # schema for validation beyond jsonschema checks. Each schema that is described in the model gets an entry.
    validation_schema = {
        "examples": {             # There should be a method `validate_examples` implemented to validate conditionals
            "id": "example_id",  # The id used to disambiguate instances of the schema. If None, an array index is used
            "name": "Example",   # The proper name for the schema
            "required_fields": [ # Any fields specified as required in the model (but not absolutely necessary for jsonschema)
                "example_id",
                "attribute_1"
            ],
            "nested_schemas": [  # Any schema instances that may be nested within instances of this schema.
                "more_examples"      # Nested instances will be validated as part of the validation of the parent.
            ]
        },
        "more_examples": {
            "id": None,
            "name": "Example 2",
            "required_fields": [],
            "nested_schemas": []
        }
    }


    def __init__(self, url, simple=False):
        self.validation_warnings = []
        self.validation_errors = []
        self.statistics = {}
        self.identifiers = {}
        self.stack_location = []
        self.schema = {}
        self.openapi_url = url
        self.json_schema = None
        self.template = None
        self.katsu_sha = None
        self.scaffold = None

        """Retrieve the schema from the supplied URL, return as dictionary."""
        try:
            osv.validate_url(self.openapi_url)
            resp = requests.get(self.openapi_url)
            resp.raise_for_status()
            schema = yaml.safe_load(resp.text)
        except Exception as e:
            print("Error reading the openapi schema, please ensure you have provided a url to a valid openapi schema.")
            print(e)
            return

        self.schema = schema["components"]["schemas"]
        sha_match = re.match(r".+Based on commit \"(.+)\".*", schema["info"]["description"])
        if sha_match is not None:
            self.katsu_sha = sha_match.group(1)
        else:
            sha_match = re.match(r".+Based on http.*katsu\/(.+)\/chord_metadata_service.*", schema["info"]["description"])
            if sha_match is not None:
                self.katsu_sha = sha_match.group(1)

        self.json_schema = openapi_to_jsonschema(resp.text, self.schema_name)

        # create the template for the schema_name schema
        self.scaffold = self.generate_schema_scaffold(self.schema[self.schema_name], list(self.validation_schema.keys())[0])
        # print(json.dumps(self.scaffold, indent=4))
        _, raw_template = self.generate_mapping_template(self.scaffold, node_name=f"{self.base_name}.INDEX")

        # add default mapping functions:
        self.template = self.add_default_mappings(raw_template)


    def warn(self, message):
        prefix = " > ".join(self.stack_location)
        if prefix.strip() == "":
            prefix = ""
        else:
            prefix += ": "
        message = prefix + message
        self.validation_warnings.append(f"{message}")


    def fail(self, message):
        prefix = " > ".join(self.stack_location)
        if prefix.strip() == "":
            prefix = ""
        else:
            prefix += ": "
        message = prefix + message
        self.validation_errors.append(f"{message}")


    def expand_ref(self, ref, validation_schema_node):
        if "$ref" in ref:
            refName = ref["$ref"].replace("#/components/schemas/", "")
            return self.generate_schema_scaffold(json.loads(json.dumps(self.schema[refName])), validation_schema_node)
        return ref["type"]


    def generate_schema_scaffold(self, schema_obj, validation_schema_node):
        result = {}
        if "type" in schema_obj:
            if schema_obj["type"] == "object":
                for prop in schema_obj["properties"]:
                    prop_obj = self.generate_schema_scaffold(schema_obj["properties"][prop], prop)
                    result[prop] = prop_obj
                if validation_schema_node in self.validation_schema:
                    nested_schemas = {}
                    for schema in self.validation_schema[validation_schema_node]["nested_schemas"]:
                        if schema in result:
                            nested_schemas[schema] = result.pop(schema)
                    for schema in nested_schemas:
                        result[schema] = nested_schemas[schema]
            elif schema_obj["type"] == "array":
                result = [self.generate_schema_scaffold(schema_obj["items"], validation_schema_node)]
            else:
                result = schema_obj["type"]
        elif "$ref" in schema_obj:
            result = self.expand_ref(schema_obj, validation_schema_node)
        elif "allOf" in schema_obj:
            result = self.expand_ref(schema_obj["allOf"][0], validation_schema_node)
        elif "oneOf" in schema_obj:
            result = self.expand_ref(schema_obj["oneOf"][0], validation_schema_node)
        elif "anyOf" in schema_obj:
            result = self.expand_ref(schema_obj["anyOf"][0], validation_schema_node)
        else:
            result = "unknown"
        return result


    def generate_mapping_template(self, node, node_name="", node_names=None):
        """Create a template for the schema, for use with the --template flag."""
        if node_names is None:
            node_names = []
        if "str" in str(type(node)):
            node_names.append(f"{node_name},")
            return "string", node_names
        elif "list" in str(type(node)):
            new_node_name = ".".join((node_name, "INDEX"))
            sc, nn = self.generate_mapping_template(node[0], new_node_name, node_names)
            return [sc], nn
        elif "number" in str(type(node)) or "integer" in str(type(node)):
            return 0, node_names
        elif "boolean" in str(type(node)):
            return True, node_names
        elif "dict" in str(type(node)):
            scaffold = {}
            node_names.append(f"{node_name},")
            for prop in node.keys():
                if node_name == "":
                    new_node_name = prop
                else:
                    new_node_name = ".".join((node_name, prop))
                scaffold[prop], node_names = self.generate_mapping_template(node[prop], new_node_name, node_names)
            return scaffold, node_names
        else:
            return str(type(node)), node_names
        return None, node_names


    def add_default_mappings(self, template):
        # if line ends in INDEX, use indexed_on
        # otherwise, single_val
        result = []
        index_stack = []
        sheet_stack = []
        for i in range(0, len(template)):
            # work with line w/o comma
            x = template[i]
            if x.startswith("##"):
                continue

            x_match = re.match(r"(.+),", x)
            if x_match is not None:
                field = x_match.group(1)
                field_bits = field.split(".")
                data_value = field_bits[-1]

                # adjust the size of the stack: if it's bigger than the number of INDEX in the line, trim the stack back
                num_indices = field_bits.count("INDEX")
                if len(index_stack) > num_indices:
                    index_stack = index_stack[0:num_indices]
                    sheet_stack = sheet_stack[0:num_indices]

                if data_value == "INDEX":
                    # base case: assume that the index_value is the last bit before the index
                    index_value = field_bits[len(field_bits)-2]

                    # clean up the sheet stack: are the last sheets still involved?
                    if len(sheet_stack) > 1:
                        while 1:
                            last_sheet = sheet_stack.pop()
                            if last_sheet == f"{self.base_name}_SHEET" or last_sheet.replace("_SHEET", "").lower() in field:
                                sheet_stack.append(last_sheet)
                                break

                    sheet_stack.append(f"{index_value.upper()}_SHEET")
                    temp = index_value.lower()
                    if f"{temp}s" in self.validation_schema:
                        temp = f"{temp}s"
                    index_value = self.validation_schema[temp]["id"]

                    # next case: data value could be the the next line's last bit:
                    next_line = template[i+1]
                    next_match = re.match(r"(.+),", next_line)
                    next_bits = next_match.group(1).split(".")
                    if field in next_line:
                        # this index is NOT a nested entry of the prev one; we need to figure out how far back to un-nest.
                        if len(index_stack) > 0:
                            prev_line = template[i-1]
                            if field not in prev_line:
                                prev_match = re.match(r"(.+),", prev_line)
                                prev_bits = prev_match.group(1).split(".")

                                # if the previous line has more indices than we have now, we have to trim the index_stack.
                                if prev_bits.count("INDEX") >= num_indices:
                                    # if prev_bits does not end on INDEX, needs to be trimmed back to its last INDEX:
                                    if prev_bits[-1] != "INDEX":
                                        while len(prev_bits) > 0:
                                            if prev_bits[-1] != "INDEX":
                                                prev_bits.pop()
                                            elif prev_bits.count("INDEX") > num_indices:
                                                prev_bits.pop()
                                            else:
                                                break

                                    # we need to figure out just how far back these differ:
                                    count = 0
                                    while 1:
                                        # if this is now the same, we're done
                                        if (".".join(prev_bits) == ".".join(field_bits)):
                                            break
                                        count += 1
                                        # bounce off the last two bits from field_bits and prev_bits
                                        field_bits.pop()
                                        field_bits.pop()
                                        prev_bits.pop()
                                        prev_bits.pop()

                                    # pop off {count} from index_stack, but stop as soon as we have fewer than the number of indices
                                    for i in range(0, count):
                                        if len(index_stack) < num_indices:
                                            break
                                        index_stack.pop()

                        # this should be added to the stack, but not if the value is "INDEX"
                        if index_value is not None and index_value != "INDEX":
                            index_stack.append(index_value)
                            if len(index_stack) > 1:
                                index_value = index_stack[-2]
                        else:
                            index_value = index_stack[-1]
                    else:
                        sheet_stack.pop()
                    x += f" {{indexed_on({sheet_stack[-1]}.{index_value})}}"
                elif data_value.endswith("date") or data_value.startswith("date"):
                    x += f" {{single_date({sheet_stack[-1]}.{data_value})}}"
                elif data_value.startswith("is_") or data_value.startswith("has_"):
                    x += f" {{boolean({sheet_stack[-1]}.{data_value})}}"
                elif data_value.startswith("number_") or data_value.startswith("age_") or "_per_" in data_value:
                    x += f" {{integer({sheet_stack[-1]}.{data_value})}}"
                else:
                    x += f" {{single_val({sheet_stack[-1]}.{data_value})}}"
                result.append(x)
        return result

    def validate_ingest_map(self, map_json):
        self.statistics["required_but_missing"] = {}
        self.statistics["schemas_used"] = []
        self.statistics["cases_missing_data"] = []

        for key in self.validation_schema.keys():
            self.validation_schema[key]["extra_args"] = {
                "index": 0
            }
        root_schema = list(self.validation_schema.keys())[0]
        for x in range(0, len(map_json[root_schema])):
            self.validate_jsonschema(map_json[root_schema][x], x)
            self.validate_schema(root_schema, map_json[root_schema][x])
        for schema in self.identifiers:
            most_common = self.identifiers[schema].most_common()
            if most_common[0][1] > 1:
                for x in most_common:
                    if x[1] > 1:
                        self.fail(f"Duplicated IDs: in schema {schema}, {x[0]} occurs {x[1]} times")
        self.statistics["schemas_not_used"] = list(set(self.validation_schema.keys()) - set(self.statistics["schemas_used"]))
        self.statistics["summary_cases"] = {
            "complete_cases": len(map_json[root_schema]) - len(self.statistics["cases_missing_data"]),
            "total_cases": len(map_json[root_schema])
        }


    def validate_jsonschema(self, map_json, index):
        for error in jsonschema.Draft202012Validator(self.json_schema).iter_errors(map_json):
            id_field = self.validation_schema[list(self.validation_schema.keys())[0]]["id"]

            # is this error a None where it's nullable?
            if error.instance is None and 'nullable' in error.schema and error.schema['nullable'] == True:
                pass # this was too hard to write as a negative statement, so the error is in the else
            else:
                root_schema = list(self.validation_schema.keys())[0]
                location = [f"{self.validation_schema[root_schema]['name']} {index}"]
                if id_field in map_json:
                    location = [map_json[id_field]]
                    curr_map = map_json
                    while len(error.path) > 1:
                        node = error.path.popleft()
                        if "str" in str(type(node)):
                            curr_map = curr_map[node]
                            idx = error.path.popleft()
                            if "str" in str(type(idx)):
                                error.path.appendleft(idx)
                                continue
                            # is there an id for this?
                            curr_map = curr_map[idx]
                            if node in self.validation_schema:
                                sch = self.validation_schema[node]
                                if "id" in sch and sch["id"] is not None and sch["id"] in curr_map:
                                    id_field = curr_map[sch["id"]]
                                else:
                                    id_field = f"{node}[{idx}]"
                            else:
                                id_field = node
                            location.append(f"{id_field}")
                    if len(error.path) > 0:
                        location.append(error.path.popleft())
                message = f"{' > '.join(location)}: {error.message}"
                self.fail(message)


    def validate_schema(self, schema_name, map_json):
        id = f"{self.validation_schema[schema_name]['name']} {self.validation_schema[schema_name]['extra_args']['index']}"
        if self.validation_schema[schema_name]["id"] is not None and self.validation_schema[schema_name]["id"] in map_json:
            id = map_json[self.validation_schema[schema_name]["id"]]
            if schema_name not in self.identifiers:
                self.identifiers[schema_name] = Counter()
            self.identifiers[schema_name].update([id])
        required_fields = self.validation_schema[schema_name]["required_fields"]
        nested_schemas = self.validation_schema[schema_name]["nested_schemas"]
        self.stack_location.append(str(id))
        case = self.stack_location[0]

        # print(f"Validating schema {schema_name} for {self.stack_location[-1]}")
        if schema_name not in self.statistics["required_but_missing"]:
            self.statistics["required_but_missing"][schema_name] = {}
        if schema_name not in self.statistics["schemas_used"]:
            self.statistics["schemas_used"].append(schema_name)

        remove_these = []
        for f in required_fields:
            if f not in self.statistics["required_but_missing"][schema_name]:
                self.statistics["required_but_missing"][schema_name][f] = {
                    "total": 0,
                    "missing": 0
                }
            self.statistics["required_but_missing"][schema_name][f]["total"] += 1
            if f not in map_json:
                # self.warn(f"{f} required for {schema_name}")
                self.statistics["required_but_missing"][schema_name][f]["missing"] += 1
                if case not in self.statistics["cases_missing_data"]:
                    self.statistics["cases_missing_data"].append(case)
                map_json[f] = None
                remove_these.append(f)

        eval(f"self.validate_{schema_name}({map_json})")
        for f in remove_these:
            map_json.pop(f)

        for ns in nested_schemas:
            if ns in map_json:
                for x in range(0, len(map_json[ns])):
                    self.validation_schema[ns]["extra_args"]["index"] = x
                    if "list" in str(type(map_json[ns])):
                        self.validate_schema(ns, map_json[ns][x])
                    else:
                        self.validate_schema(ns, map_json[ns])
        self.stack_location.pop()
