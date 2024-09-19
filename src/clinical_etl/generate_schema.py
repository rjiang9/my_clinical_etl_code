#!/usr/bin/env python
# coding: utf-8

from copy import deepcopy
import importlib.util
from importlib.metadata import files, version
import json
import mappings
import os
import pandas
import sys
import argparse
from mohschemav2 import MoHSchemaV2
from mohschemav3 import MoHSchemaV3
import re


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, help="URL to openAPI schema file (raw github link)", default="https://raw.githubusercontent.com/CanDIG/katsu/develop/chord_metadata_service/mohpackets/docs/schema.yml")
    parser.add_argument('--schema', type=str, help="Name of schema class", default="MoHSchemaV3")
    parser.add_argument('--out', type=str, help="name of output file; csv extension will be added. Default is template", default="template")
    args = parser.parse_args()
    return args


def main(args):
    url = args.url
    schema_name = args.schema
    schema_class = schema_name.lower()
    mod = importlib.import_module(schema_class)
    schema = eval(f'mod.{schema_name}(url)')
    if schema is None:
        print("Did not find an openapi schema at {}; please check link".format(url))
        return

    outputfile = "{}.csv".format(args.out)

    metadata = f"## Schema generated from {url}\n"
    if schema.katsu_sha is not None:
        metadata += f"## Based on repo commit sha \"{schema.katsu_sha}\"\n"

    node_names = schema.template

    with open(outputfile, 'w') as f:  # write to csv file for mapping
        f.write(metadata)
        f.write("## Items are comma separated: element, mapping method\n")
        # f.write("## (.INDEX is an array element) (* is required) (+ denotes ontology term),\n")
        for nn in node_names:
            f.write(f"{nn}\n")
    print(f"Template written to {outputfile}")
    return

if __name__ == '__main__':
    main(parse_args())

