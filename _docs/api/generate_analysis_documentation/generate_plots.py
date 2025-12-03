from __future__ import print_function  

import csv 
import json
import os
import re
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.ticker import FuncFormatter
import seaborn as sns

DATA_FOLDER = "descriptors_data"  # json files for each descriptor extracted from DB
OUT_FOLDER = "../source/_static/descriptors"

with open("descriptors.csv", "r", newline="") as f:
    reader = csv.reader(f)
    next(reader)
    descriptor_names = [row[0] for row in reader]

print("Descriptors found:", len(descriptor_names))

def sort_key(s):
    ''' Sort string labels, and fix note order. '''
    m = re.match(r"([A-Za-z]+)(#?)(\d+)", s)
    if m:
        letter, symbol, number = m.groups()
        return (int(number), letter.lower(), symbol != "")
    else:
        return (float('inf'), s.lower(), False)
    
def plot_histogram(data, label, out_folder):
    sns.set_theme(style="whitegrid", context="talk", palette="pastel")
    plt.figure(figsize=(8,5))

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
            )
        
    else:  # Categorical/string data
        if len_vals > 20: 
            plt.figure(figsize=(15,5))
            plt.xticks(rotation=60) 
        if len_vals > 100: 
            data = data.value_counts().nlargest(20).index
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
    plt.gca().yaxis.set_major_formatter(FuncFormatter(thousands_formatter))

    plt.xticks(fontsize=10)
    plt.yticks(fontsize=10)
    plt.title(label, fontsize=11)
    plt.xlabel("Value", fontsize=10)
    plt.ylabel("Frequency (sound count)", fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.2)
    plt.tight_layout()
    
    plt.savefig(f"{out_folder}/{label}.png", dpi=150)
    plt.close()


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
            label = f"{descriptor_name}_{i}"
            print(f"\tDim. {i}")
            plot_histogram(pool, label, OUT_FOLDER)