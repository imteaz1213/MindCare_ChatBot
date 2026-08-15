"""
Converts the Bengali empathetic conversations corpus (instruction /
Topics / Question-Title / input / output CSV) into JSONL formatted for
fine-tuning.

Usage:
    python scripts/prepare_finetune_data.py --input data/finetune_corpus.csv --format openai
    python scripts/prepare_finetune_data.py --input data/finetune_corpus.csv --format hf

This is an OFFLINE step -- run it once to produce a training file, then
fine-tune with your provider of choice. The Flask app does not call
this script at runtime.
"""

import argparse
import json
import pandas as pd


def to_openai_format(df: pd.DataFrame) -> list:
    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "messages": [
                    {"role": "system", "content": str(row["instruction"])},
                    {"role": "user", "content": str(row["input"])},
                    {"role": "assistant", "content": str(row["output"])},
                ]
            }
        )
    return records


def to_hf_format(df: pd.DataFrame) -> list:
    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "instruction": str(row["instruction"]),
                "input": str(row["input"]),
                "output": str(row["output"]),
            }
        )
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to the corpus CSV")
    parser.add_argument("--output", default=None, help="Path for the output JSONL")
    parser.add_argument(
        "--format", choices=["openai", "hf"], default="openai",
        help="openai = chat fine-tuning format, hf = instruction/input/output format",
    )
    args = parser.parse_args()

    output_path = args.output or args.input.rsplit(".", 1)[0] + f"_{args.format}.jsonl"

    df = pd.read_csv(args.input)
    df = df.dropna(subset=["instruction", "input", "output"])
    df = df.drop_duplicates(subset=["input"])

    records = to_openai_format(df) if args.format == "openai" else to_hf_format(df)

    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} records to {output_path}")


if __name__ == "__main__":
    main()
