import subprocess


def main():
    docs = subprocess.check_output(["pdoc",  "mappings"])
    print(docs.decode())
    with open("../../mapping_functions.md", "r") as f:
        mapping_functions_lines = f.readlines()

    updated_mapping_functions = []
    for line in mapping_functions_lines:
        if line.startswith("# Standard Functions Index"):
            break
        else:
            updated_mapping_functions.append(line)
    updated_mapping_functions.append("# Standard Functions Index\n")
    updated_mapping_functions.append(
        "\n<!--- documentation below this line is generated automatically by running generate_mapping_docs.py --->\n\n")
    updated_mapping_functions.append(docs.decode())
    with open("../../mapping_functions.md", "w+") as f:
        f.writelines(updated_mapping_functions)


if __name__ == '__main__':
    main()
