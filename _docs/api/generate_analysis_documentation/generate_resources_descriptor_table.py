import csv

# Copy paste as the second table of the Sound Instance. 
# If the descriptors change, we should change the resources docs too.

def generate_rst_table(csv_file):
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader]

    # Table headers
    display_headers = ["Field name", "Type", "Filtering", "Description"]

    # Determine column widths
    col_widths = [len(h) for h in display_headers]
    for row in rows:
        col_widths[0] = max(col_widths[0], len(row['Descriptor name'])+2)
        col_widths[1] = max(col_widths[1], len(row['Type']))
        col_widths[2] = max(col_widths[2], 6)
        col_widths[3] = max(col_widths[3], len(row['Description']))

    sep_line = "  ".join("=" * w for w in col_widths)
    header_line = "  ".join(f"{h:<{w}}" for h, w in zip(display_headers, col_widths))
    table_lines = [sep_line, header_line, sep_line]

    links = []
    base_url = "https://freesound.org/docs/api/analysis_docs.html#"

    for row in rows:
        ref_name = row['Descriptor name']
        ref_name_hyphen = ref_name.replace('_', '-')
        filtered_value = 'yes' if 'array' not in row['Type'] else 'no'

        # Table with referenced descriptor name and 3 more columns
        table_lines.append(
            f"{ref_name+'_':<{col_widths[0]}}  "
            f"{row['Type']:<{col_widths[1]}}  "
            f"{filtered_value:<{col_widths[2]}}  "
            f"{row['Description']:<{col_widths[3]}}"
        )
        # Collect the URI reference
        links.append(f".. _{ref_name}: {base_url}{ref_name_hyphen}")

    table_lines.append(sep_line)
    table_lines.append("")
    table_lines.extend(links)

    return "\n".join(table_lines)


if __name__ == "__main__":
    csv_file = "descriptors.csv" 
    table = generate_rst_table(csv_file)
    print(table)

