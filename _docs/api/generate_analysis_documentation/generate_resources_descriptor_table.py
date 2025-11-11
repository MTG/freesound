import csv

# Copy paste to Search resources -> Search -> filter parameter. 
# If the descriptors change, we should change the docs for search too.

def generate_rst_table(csv_file):
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if 'array' not in r['Type']]  # discard array descriptors, not for filtering

    # Table headers
    display_headers = ["Filter name", "Type", "Description"]

    col_widths = [len(h) for h in display_headers]
    for row in rows:
        col_widths[0] = max(col_widths[0], len(row['Descriptor name'])+1)
        col_widths[1] = max(col_widths[1], len(row['Type']))
        col_widths[2] = max(col_widths[2], len(row['Description']))

    sep_line = "  ".join("=" * w for w in col_widths)
    header_line = "  ".join(f"{h:<{w}}" for h, w in zip(display_headers, col_widths))
    table_lines = [sep_line, header_line, sep_line]

    links = []
    base_url = "https://freesound.org/docs/api/analysis_docs.html#"

    for row in rows:
        # Table shows descriptor name with reference
        ref_name = row['Descriptor name']
        table_lines.append(
            f"{ref_name+'_':<{col_widths[0]}}  "
            f"{row['Type']:<{col_widths[1]}}  "
            f"{row['Description']:<{col_widths[2]}}"
        )
        # Collect the URL reference
        links.append(f".. _{ref_name}: {base_url}{ref_name}")

    table_lines.append(sep_line)
    table_lines.append("")
    table_lines.extend(links)

    return "\n".join(table_lines)


if __name__ == "__main__":
    csv_file = "descriptors.csv" 
    table = generate_rst_table(csv_file)
    print(table)


