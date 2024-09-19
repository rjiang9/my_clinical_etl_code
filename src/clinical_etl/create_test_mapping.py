from copy import deepcopy
import json
import os
import re
from CSVConvert import create_mapping_scaffold, generate_mapping_template
import argparse
from chord_metadata_service.mcode.schemas import MCODE_SCHEMA


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--template', type=str, help="Path to a template mapping file.")
    parser.add_argument('--placeholder', type=str, default="abcd", help="Value for placeholder strings.")
    args = parser.parse_args()
    return args


def map_to_mcodepacket(placeholder_val, node, schema):
    # walk through the provided node of the mcodepacket and fill in the details
    if "str" in str(type(node)):
        return pick_value_for_node(placeholder_val, node, schema)
    elif "list" in str(type(node)):
        new_node = []
        for i in range(0,len(node)):
            m = map_to_mcodepacket(placeholder_val, node[i], schema["items"])
            if "list" in str(type(m)):
                new_node = m
            else:
                new_node.append(m)
        return new_node
    elif "dict" in str(type(node)):
        scaffold = {}
        for key in node.keys():
            x = map_to_mcodepacket(placeholder_val, node[key], schema["properties"][key])
            if x is not None:
                scaffold[key] = x
        return scaffold


def pick_value_for_node(placeholder_val, node, schema):
    # flatten to only one thing if it's oneOf:
    if "oneOf" in schema:
        schema = schema['oneOf'][0]
        return map_to_mcodepacket(placeholder_val, node, schema)
    if "anyOf" in schema:
        schema = schema['anyOf'][0]
        return map_to_mcodepacket(placeholder_val, node, schema)
    
    # break down objects:
    if "type" in schema:
        if schema["type"] == "object":
            obj = {}
            if "properties" in schema:
                for k in schema["properties"].keys():
                    obj[k] = pick_value_for_node(placeholder_val, node, schema["properties"][k])
            if len(obj.keys()) == 0:
                obj["value"] = placeholder_val
            return obj
        elif schema["type"] == "array":
            if "items" in schema:
                return pick_value_for_node(placeholder_val, node, schema["items"])
        elif schema["type"] == "boolean":
            return True
        elif schema["type"] == "string":
            if "enum" in schema:
                return schema["enum"][0]
            if "format" in schema and schema["format"] == "date-time":
                return "2022-07-17T17:17:17.085021Z"
            if "description" in schema:
                # it's useful if there's an example!
                eg_match = re.match(r".*(e\. *g\. *)(.+?)(\s).*", schema["description"])
                if eg_match is not None:
                    return eg_match.group(2)
                
                # if it's a timestamp, just stick in a placeholder date:
                if "date " in schema["description"]:
                    return "2000-11-01"
                if "timestamp" in schema["description"]:
                    return "2000-04-05T14:30"
                if "CURIE-style" in schema["description"]:
                    return "UNK:0000"
            return placeholder_val
        # else:
            # return placeholder_val
    return schema


def main(args):
    template = args.template
    if template is not None:
        with open(template, 'r') as f:
            mapping = f.readlines()
    else:
        schema, mapping = generate_mapping_template(MCODE_SCHEMA)
    mapping_scaffold = create_mapping_scaffold(mapping, test=True)
    # print(json.dumps(mapping_scaffold, indent=4))
    if mapping_scaffold is None:
        print("No mapping scaffold was loaded. Either katsu was not found or no schema was specified.")
        return

    mcodepackets = [map_to_mcodepacket(args.placeholder, deepcopy(mapping_scaffold), MCODE_SCHEMA)]

    if template is not None:
        output_file, ext = os.path.splitext(template)
        with open(f"{output_file}_testmap.json", 'w') as f:    # write to json file for ingestion
            json.dump(mcodepackets, f, indent=4)
        print(f"Test mapping saved as {output_file}_testmap.json")
    else:
        print(json.dumps(mcodepackets, indent=4))

if __name__ == '__main__':
    main(parse_args())
