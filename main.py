import os
import sys
import time

from colorama import init, Fore, Style

init()


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def run_local_script():
    os.system('python port_details_local_to_csv.py')


def run_remote_script():
    os.system('python port_details_remote_to_csv.py')


def main_menu():
    while True:
        clear_screen()
        print('=' * 60)
        print(Fore.CYAN + "Nokia SROS Port Details Processor: Local & Remote to CSV" + Style.RESET_ALL)
        print('=' * 60)
        print("1. Process Local Port Details to CSV")
        print("2. Process Remote Port Details to CSV")
        print("3. Exit")
        print('-' * 60)
        choice = input(Fore.YELLOW + "Enter your choice (1-3): " + Style.RESET_ALL)

        if choice == '1':
            clear_screen()
            print(Fore.CYAN + "Processing local log files..." + Style.RESET_ALL)
            run_local_script()
        elif choice == '2':
            clear_screen()
            print(Fore.CYAN + "Processing remote devices..." + Style.RESET_ALL)
            run_remote_script()
        elif choice == '3':
            print(Fore.YELLOW + "Exiting the program. Goodbye!" + Style.RESET_ALL)
            time.sleep(2)
            sys.exit(0)
        else:
            print(Fore.RED + "Invalid choice. Please try again." + Style.RESET_ALL)
            input(Fore.MAGENTA + "Press Enter to continue..." + Style.RESET_ALL)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Program interrupted by user. Exiting...{Style.RESET_ALL}")
        time.sleep(2)
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}An unexpected error occurred: {e}{Style.RESET_ALL}")
        time.sleep(2)
        sys.exit(1)
    except BaseException as be:
        # This block will catch `KeyboardInterrupt` if it hasn't been caught earlier
        print(f"\n{Fore.YELLOW}Caught BaseException (likely KeyboardInterrupt). Exiting...{Style.RESET_ALL}")
        time.sleep(2)
        sys.exit(0)
