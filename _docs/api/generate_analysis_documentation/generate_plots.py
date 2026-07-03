from __future__ import print_function  

import argparse
import csv 
import json
import os
import re
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.ticker import FuncFormatter
import seaborn as sns
import numpy as np

DATA_FOLDER = "audio_descriptors_values"  # json files for each descriptor extracted from DB
OUT_FOLDER = "../source/_static/descriptors"

def sort_key(s):
    ''' Sort string labels, and fix note order. '''
    m = re.match(r"([A-Za-z]+)(#?)(\d+)", s)
    if m:
        letter, symbol, number = m.groups()
        return (int(number), letter.lower(), symbol != "")
    else:
        return (float('inf'), s.lower(), False)
    
def plot_histogram(data, label, out_folder, remove_outliers=True):
    sns.set_theme(style="whitegrid", context="talk", palette="pastel")
    plt.figure(figsize=(8,5))

    if remove_outliers and all(isinstance(x, (int, float)) for x in data) and not set(data).issubset({0, 1}):
        q1 = np.percentile(data, 5)
        q3 = np.percentile(data, 95)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        data = [x for x in data if lower_bound <= x <= upper_bound]

    len_vals = len(set(data))
    bins = 100 if len_vals > 100 else len_vals

    if all(isinstance(x, (int, float)) for x in data):  # Numeric data
        if set(data).issubset({0, 1}):  # Boolean data
            sns.countplot(
                x=data,
                color=sns.color_palette("Set2")[0]
            )
            plt.xticks(ticks=[0, 1], labels=["no (0)", "yes (1)"])
        else:
            sns.histplot(
                data,
                bins=bins,
                kde=True,
                color=sns.color_palette("Set2")[0],
                discrete=False,
                stat="percent"
            )
        
    else:  # Categorical/string data
        if len_vals > 20: 
            plt.figure(figsize=(15,5))
            plt.xticks(rotation=60) 
        if len_vals > 100: 
            # Keep only the 20 most frequent categories while preserving counts.
            top_labels = {label for label, _ in Counter(data).most_common(20)}
            data = [value for value in data if value in top_labels]
        sorted_data = sorted(set(data), key=sort_key)
        sns.countplot(
            x=data,
            color=sns.color_palette("Set2")[0],
            order=sorted_data
        )
        
    def thousands_formatter(x, pos):
        if x >= 1000:
            return f'{int(x/1000)}k'
        return int(x)
    plt.gca().ticklabel_format(style='plain', axis='y')
    #plt.gca().yaxis.set_major_formatter(FuncFormatter(thousands_formatter))

    plt.xticks(fontsize=10)
    plt.yticks(fontsize=10)
    plt.title(label, fontsize=11)
    plt.xlabel("Value", fontsize=10)
    plt.ylabel("Frequency (%)", fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.2)
    plt.tight_layout()
    
    plt.savefig(f"{out_folder}/{label}.png", dpi=150)
    plt.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate descriptor plots from JSON value dumps."
    )
    parser.add_argument(
        "--only",
        default="",
        help="Process only descriptors whose name contains this string"
    )
    parser.add_argument(
        "--exclude",
        default="",
        help="Skip descriptors whose name contains this string"
    )
    args = parser.parse_args()

    with open("descriptors.csv", "r", newline="") as f:
        reader = csv.reader(f)
        next(reader)
        descriptor_names = [row[0] for row in reader]

    print("Descriptors found:", len(descriptor_names))

    if args.only:
        descriptor_names = [d for d in descriptor_names if args.only in d]
    if args.exclude:
        descriptor_names = [d for d in descriptor_names if args.exclude not in d]

    print("Descriptors selected after filters:", len(descriptor_names))

    # Plot all descriptors
    for descriptor_name in descriptor_names: 
        json_path = os.path.join(DATA_FOLDER, f"{descriptor_name}.json")
        if not os.path.isfile(json_path):
            print(f"File not found: {json_path}, skipping")
            continue

        with open(json_path, "r") as f:
            values = json.load(f)
        values = [v for v in values if v is not None]
        print(f"Processing {descriptor_name} ..")

        if not values:
            print(f"Skipping {descriptor_name} (empty)")
            continue

        first_val = values[0]

        # Single-value number descriptor (integer and/or float, boolean)
        if isinstance(first_val, (int, float, str)):
            plot_histogram(values, descriptor_name, OUT_FOLDER)

        # Vector descriptor with numbers or strings
        elif isinstance(first_val, (list, tuple)):
            if len({len(v) for v in values}) != 1:  # skip varying-length ones
                print(f"Skipping {descriptor_name}: varying-length descriptor")
                continue

            for i in range(len(first_val)):
                pool = [v[i] for v in values if len(v) > i]
                label = f"{descriptor_name}-{i}"
                print(f"\tDim. {i}")
                plot_histogram(pool, label, OUT_FOLDER)