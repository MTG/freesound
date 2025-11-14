from __future__ import print_function  

import csv 
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns


DATA_FOLDER = "descriptors_data"  # json files for each descriptor extracted from DB
OUT_FOLDER = "out_plots"  # Must be created, transfer diagrams to "_static/descriptors"

with open("descriptors.csv", "r", newline="") as f:
    reader = csv.reader(f)
    next(reader)
    descriptor_names = [row[0] for row in reader]

print("Descriptors found:", len(descriptor_names))

#### fake data #######
# TODO: extract data directly from DB
# data types: float/int (single number), string, boolean, vector numeric, vector string
import random
import string
NUM_VALUES = 50000
descriptors = {
    "d1": lambda: round(random.uniform(0, 500), 2),  # floats
    "d2": lambda: random.randint(10, 50),  # integers
    "d3": lambda: random.choice(['aaa', 'bbb', 'ccc']),  # strings
    "d4": lambda: random.choice([0, 1]),  # boolean
    "d5": lambda: [round(random.uniform(0.5, 0.75), 2), round(random.uniform(0.9, 1.5), 2)],  # vector of numbers
    "d6": lambda: [random.choice(string.ascii_letters) for _ in range(3)],  # vector of strings
}
for name, generator in descriptors.items():  # each descriptor as its own JSON file
    data = [generator() for _ in range(NUM_VALUES)]
    with open(os.path.join(DATA_FOLDER, f"{name}.json"), "w") as f:
        json.dump(data, f, indent=2)
    print(f"{name}.json written with {NUM_VALUES} values")
######################


sns.set_theme(style="whitegrid", context="talk", palette="pastel")

def plot_histogram(data, label, out_folder):
    plt.figure(figsize=(8,5))

    len_vals = len(set(data))
    if len_vals > 100:
        bins = 100
    else:
        bins = len_vals

    if all(isinstance(x, (int, float)) for x in data):  # Numeric data
        if set(data).issubset({0, 1}):  # boolean
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
        sns.countplot(
            x=data,
            color=sns.color_palette("Set2")[0]
        )
        
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
for descriptor_name in descriptors.keys():  # TODO: plug real data
    json_path = os.path.join(DATA_FOLDER, f"{descriptor_name}.json")
    if not os.path.isfile(json_path):
        print(f"File not found: {json_path}, skipping")
        continue

    with open(json_path, "r") as f:
        values = json.load(f)
    print(f"Processing {descriptor_name} ..")

    if not values:
        print(f"Skipping {descriptor_name} (empty)")
        continue

    first_val = values[0]

    # Single-value number descriptor (integer and/or float, boolean)
    if isinstance(first_val, (int, float, str)):
        if set(values).issubset({0,1}):
            print(f"Boolean descriptor: {descriptor_name}")
        else:
            print(f"Single-number descriptor: {descriptor_name}")
        plot_histogram(values, descriptor_name, OUT_FOLDER)

    # Vector descriptor with numbers or strings
    elif isinstance(first_val, (list, tuple)):
        if len({len(v) for v in values}) != 1:  # skip varying-length ones
            print(f"Skipping {descriptor_name}: varying-length descriptor")
            continue

        for i in range(len(first_val)):
            pool = [v[i] for v in values if len(v) > i]
            label = f"{descriptor_name}_{i}"
            print(f"\tDim. {i} of {descriptor_name}")
            plot_histogram(pool, label, OUT_FOLDER)