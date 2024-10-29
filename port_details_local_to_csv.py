import csv
import os
import re
import sys

import textfsm
from colorama import Fore, init, Style

init()


def count_files_in_directory(input_dir):
    # List all files in the directory
    files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
    return len(files)


def process_files(input_dir, output_dir, template_file):
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Process each .log or .txt file in the input directory
    for filename in os.listdir(input_dir):
        if filename.endswith(('.log', '.txt')):  # Process both .log and .txt files
            input_file = os.path.join(input_dir, filename)
            csv_output_file = os.path.join(output_dir, filename.replace('.log', '.csv').replace('.txt', '.csv'))

            try:
                # Parse the output
                structured_data = parse_output(input_file, template_file)

                # Save to CSV
                save_to_csv(structured_data, csv_output_file)

                # Print success message
                print(
                    Fore.GREEN + f"[SUCCESS] Processed {filename} to CSV. Saved as '{csv_output_file}'." + Style.RESET_ALL)

            except Exception as e:
                # Print error message in case of failure
                print(Fore.RED + f"[ERROR] Failed to process {filename}: {e}" + Style.RESET_ALL)


def parse_output(input_file, template_file):
    # Read the command output from the file
    with open(input_file, 'r') as f:
        command_output = f.read()

    # Read the TextFSM template
    with open(template_file, 'r') as f:
        fsm_template = textfsm.TextFSM(f)

    # Parse the output using TextFSM
    parsed_data = fsm_template.ParseText(command_output)

    # Get the parsed data in a structured format
    structured_data = []
    table_headers = fsm_template.header
    for entry in parsed_data:
        structured_data.append(dict(zip(table_headers, entry)))

    return structured_data


def save_to_csv(structured_data, csv_file):
    # Save the structured data to a CSV file with specific formatting
    with open(csv_file, 'w', newline='') as csvfile:
        # Prepare headers, including a new 'LAG' column
        existing_keys = list(structured_data[0].keys())
        headers = existing_keys[:2] + ['Lag'] + existing_keys[2:]
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for row in structured_data:
            # Initialize LAG to an empty string for each row
            lag_value = ''
            opera_state_column = row.get('OperState', '')
            # Check the OperState for specific conditions
            if 'Active in LAG' in opera_state_column or 'Standby in LAG' in opera_state_column:
                # Extract the LAG number using regex
                match = re.search(r'-(\s+(?:Active|Standby) in LAG\s+(\d+))', opera_state_column)
                if match:
                    lag_value = f'{match.group(2)}'  # Set the LAG value
                    # Set OperState to 'up' or 'standby' based on the first part of the string
                    row['OperState'] = opera_state_column.split()[0]  # Get 'up' or 'standby'
            else:
                lag_value = '-'  # Set -

            # Assign the lag_value to the LAG column
            row['Lag'] = lag_value

            # Convert the second column to text format
            if len(row) > 1:
                second_col_key = list(row.keys())[1]  # Get the second column key
                row[second_col_key] = "'" + str(row[second_col_key])  # Convert to string

            # Write the updated row to CSV
            writer.writerow(row)


if __name__ == '__main__':
    # Directory and file paths
    input_directory = 'Input'
    output_directory = 'Output'
    template_file_path = 'Lib/nokia_sros_show_port_detail.template'  # Update with your TextFSM template path

    num_files = count_files_in_directory(input_directory)
    print(Fore.LIGHTYELLOW_EX + f'Number of files in the directory: {num_files}' + Style.RESET_ALL)

    # Process all files
    process_files(input_directory, output_directory, template_file_path)

    input(Fore.MAGENTA + "\nAll files are processed, Press enter to exit >" + Style.RESET_ALL)
    sys.exit()
