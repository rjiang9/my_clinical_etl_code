import argparse
import json


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=str, required=True, help="Path to input json file"
    )
    args = parser.parse_args()
    return args


def generate_csv(input_path):
    output_path = input_path.replace("_map.json", "_completeness.csv")
    print(f"Converting {input_path} to {output_path}")
    with open(input_path) as f:
        stats_dict = json.load(f)["statistics"]
        with open(output_path, "w") as out:
            out.write("Schema,Field,Total,Missing,Fraction_missing\n")
            required_but_missing = stats_dict["required_but_missing"]
            for k, v in required_but_missing.items():
                for field, stats in v.items():
                    total = stats["total"]
                    missing = stats["missing"]
                    fraction = missing / total
                    out.write(f"{k},{field},{total},{missing},{round(fraction,2)}\n")


if __name__ == "__main__":
    args = parse_args()
    input_path = args.input
    generate_csv(input_path)
