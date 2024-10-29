import csv
import getpass
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

import textfsm
from colorama import init, Fore, Style
from netmiko import (
    ConnectHandler,
    NetMikoTimeoutException,
    NetMikoAuthenticationException,
)
from paramiko.ssh_exception import SSHException

init()


def read_devices(ips_file: str) -> List[str]:
    # Check devices.txt file if it doesn't exist
    if not os.path.isfile(ips_file):
        print(
            Fore.LIGHTRED_EX
            + f"\r[ERROR] File '{ips_file}' not found.\n"
            + Style.RESET_ALL
        )
        input(Fore.MAGENTA + "Press enter to exit >" + Style.RESET_ALL)
        sys.exit(1)

    # Read device IPs from a file.
    with open(ips_file, "r") as f:
        devices = [line.strip() for line in f if line.strip()]

    if not devices:
        print(
            Fore.LIGHTRED_EX
            + f"[ERROR] No devices found in the file '{ips_file}'."
            + Style.RESET_ALL
        )
        input(Fore.MAGENTA + "Press enter to exit >" + Style.RESET_ALL)
        sys.exit(1)

    return devices


def get_credentials():
    # Get username and password from user input.
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    return username, password


def process_device(
        device_ip: str,
        username: str,
        password: str,
        command: str,
        template_file: str,
        output_dir: str,
) -> str:
    """Process a single device: connect, execute command, parse output, and save to CSV."""
    try:
        result = connect_and_execute(device_ip, username, password, command)
        device_show_result = result[0]
        host_name = result[1]
        parsed_show_data = parse_output_with_textfsm(device_show_result, template_file)
        log_time = time.strftime("%Y-%m-%d_%H-%M-%S")
        os.makedirs(output_dir, exist_ok=True)
        csv_file = os.path.join(output_dir, f"{host_name}_{device_ip}_{log_time}.csv")
        with open(csv_file, "w", newline="") as csvfile:
            # Prepare headers, including a new 'LAG' column
            existing_keys = list(parsed_show_data[0].keys())
            headers = existing_keys[:2] + ['Lag'] + existing_keys[2:]
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()

            for row in parsed_show_data:
                # Initialize LAG to an empty string for each row
                lag_value = ""
                opera_state_column = row.get("OperState", "")
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
                row["Lag"] = lag_value

                # Convert the second column to text format
                if len(row) > 1:
                    second_col_key = list(row.keys())[1]  # Get the second column key
                    row[second_col_key] = "'" + str(
                        row[second_col_key]
                    )  # Convert to string

                # Write the updated row to CSV
                writer.writerow(row)

        return f"[SUCCESS] Data collected from {device_ip}. Saved as {csv_file}"
    except Exception as e:
        return f"[ERROR] processing {device_ip}: {str(e)}"


def connect_and_execute(
        device_ip: str, username: str, password: str, command: str
) -> str:
    """Connect to a device using Netmiko and execute a command."""
    device = {
        "device_type": "nokia_sros",
        "ip": device_ip,
        "username": username,
        "password": password,
        "read_timeout_override": 90,
    }

    try:
        with ConnectHandler(**device, global_delay_factor=2) as connection:
            prompt_hostname = connection.find_prompt()[0:-1]
            host_name = re.split(":", prompt_hostname)
            if len(host_name) > 1:
                host_name = host_name[1]
            else:
                host_name = device_ip  # Fallback to IP address if the prompt does not contain the expected format

            device_show_result = connection.send_command(command, delay_factor=1)
            connection.disconnect()
            return device_show_result, host_name

    except NetMikoTimeoutException:
        raise Exception(f"Host unreachable")
    except NetMikoAuthenticationException:
        raise Exception(f"Authentication failure-> Login '{username}'")
    except SSHException:
        raise Exception(f"SSH Issue")

def parse_output_with_textfsm(device_show_result: str, template_file: str) -> List[Dict[str, str]]:
    """Parse the command output using a TextFSM template."""
    try:
        with open(template_file, "r") as f:
            template = textfsm.TextFSM(f)
        parsed_show_data = template.ParseText(device_show_result)
        return [dict(zip(template.header, entry)) for entry in parsed_show_data]
    except Exception as e:
        raise Exception(f"Error parsing output with TextFSM: {str(e)}")


def main():
    devices = read_devices("Lib/devices.txt")
    print(Fore.LIGHTYELLOW_EX + f'Number of devices : {len(devices)}' + Style.RESET_ALL)
    username, password = get_credentials()
    command = "show port detail"
    template_file = (
        "Lib/nokia_sros_show_port_detail.template"
    )
    output_dir = "Output"
    # Check nokia_sros_show_port_detail.template file if it doesn't exist
    if not os.path.isfile(template_file):
        print(
            Fore.LIGHTRED_EX
            + f"[ERROR] TextFSM template file '{template_file}' not found."
            + Style.RESET_ALL
        )
        input(Fore.MAGENTA + "Press enter to exit >" + Style.RESET_ALL)
        sys.exit(1)

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_device = {
            executor.submit(
                process_device,
                device,
                username,
                password,
                command,
                template_file,
                output_dir,
            ): device
            for device in devices
        }
        for future in as_completed(future_to_device):
            device = future_to_device[future]
            try:
                result = future.result()
                if "[ERROR]" in result:
                    print(Fore.RED + result + Style.RESET_ALL)
                else:
                    print(Fore.GREEN + result + Style.RESET_ALL)
            except Exception as exc:
                print(
                    Fore.RED
                    + f"[ERROR] {device} generated an exception: {exc}"
                    + Style.RESET_ALL
                )

    input(Fore.MAGENTA + "\nAll devices processed, Press enter to exit >" + Style.RESET_ALL)
    sys.exit()


if __name__ == "__main__":
    main()
