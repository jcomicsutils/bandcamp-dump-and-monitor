import subprocess
import time
import os
import sys
import re
from datetime import datetime

# --- Configuration ---
# The name of the shell script you want to run.
SCRIPT_TO_RUN = "bandcamp-dump"

# The file containing the list of URLs to download.
URL_LIST_FILE = "bandcamp-dump.lst"

# The file to log URLs that were removed due to repeated failures.
REMOVED_LOG_FILE = "removed.txt"

# The command to execute the script.
COMMAND = ["bash", SCRIPT_TO_RUN]

# The string that indicates the entire queue has completed successfully.
SUCCESS_MESSAGE = "--> All downloads finished."

# The number of times a URL can fail before it's removed.
MAX_FAILURES = 5

# The time to wait in seconds after the script stops before restarting it.
WAIT_TIME_SECONDS = 15

def is_list_file_empty(filename):
    """
    Checks if the URL list file is non-existent or only contains whitespace.
    """
    if not os.path.isfile(filename):
        return True
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    # Found a non-empty line
                    return False
        # No non-empty lines were found
        return True
    except Exception as e:
        print(f"\nError checking if file is empty '{filename}': {e}")
        # Assume it's not empty to prevent accidental deletion
        return False

def remove_urls_from_list(urls_to_remove, filename):
    """
    Safely removes a list of URLs from the given file.
    """
    if not urls_to_remove:
        return
    if not os.path.isfile(filename):
        print(f"Warning: URL list file '{filename}' not found. Cannot remove URL(s).")
        return

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        lines_to_keep = []
        for line in lines:
            should_keep = True
            for url in urls_to_remove:
                if url in line:
                    should_keep = False
                    break
            if should_keep:
                lines_to_keep.append(line)

        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(lines_to_keep)
        
        print(f"Successfully updated '{filename}'. Removed {len(urls_to_remove)} URL(s).")

    except Exception as e:
        print(f"\nError trying to remove URLs from '{filename}': {e}")

def log_removed_url(url, reason_summary, full_log):
    """
    Appends a removed URL and the detailed reason/log to the log file.
    """
    try:
        with open(REMOVED_LOG_FILE, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] URL: {url}\n")
            f.write(f"          Reason: {reason_summary}\n")
            f.write(f"--- Full Log ---\n{full_log.strip()}\n--- End Log ---\n\n")
        print(f"Logged removed URL and full error to '{REMOVED_LOG_FILE}'.")
    except Exception as e:
        print(f"Error writing to log file '{REMOVED_LOG_FILE}': {e}")


def main():
    """
    Main function to run the monitoring and restarting logic.
    """
    monitor_script_name = sys.argv[0]
    if not os.path.isfile(SCRIPT_TO_RUN):
        print(f"Error: The script '{SCRIPT_TO_RUN}' was not found in this directory.")
        sys.exit(1)

    # This dictionary will persist across bandcamp-dump restarts, but not monitor.py restarts.
    failure_counts = {}
    urls_to_remove_this_run = []

    print("--- Script Monitor Started ---")
    print(f"Monitoring: '{' '.join(COMMAND)}'")
    print(f"Max failures per URL: {MAX_FAILURES}")
    print(f"Will stop when it sees: '{SUCCESS_MESSAGE}'")
    print("Press Ctrl+C to stop the monitor.")
    print("-" * 30)

    try:
        while True:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting '{SCRIPT_TO_RUN}'...")

            current_url = None
            urls_to_remove_this_run = []
            # Buffer to hold output for the current download attempt
            output_buffer = []
            
            process = subprocess.Popen(
                COMMAND,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )

            all_finished = False

            with process.stdout:
                for line in iter(process.stdout.readline, ''):
                    print(line, end='')
                    output_buffer.append(line)

                    if "--> Downloading:" in line:
                        # New download starting, clear the buffer to start fresh
                        output_buffer = [line]
                        current_url = line.split("--> Downloading:")[1].strip().split()[0]
                        print(f"INFO: Now monitoring progress for URL: {current_url}")

                    match = re.search(r'\((\d+)/(\d+)\)\s*\[=*\]\s*::\s*Finished:', line)
                    if match:
                        num1, num2 = int(match.group(1)), int(match.group(2))
                        
                        if num1 > 0 and num1 == num2 and current_url:
                            print(f"\nINFO: Download complete for {current_url}. Queuing for removal.")
                            if current_url not in urls_to_remove_this_run:
                                urls_to_remove_this_run.append(current_url)
                            # Reset failure count on success
                            if current_url in failure_counts:
                                del failure_counts[current_url]
                            current_url = None
                            # Clear buffer on success
                            output_buffer = []

                    if SUCCESS_MESSAGE in line:
                        print("\n\n--- Completion Message Detected ---")
                        all_finished = True
                        break

            return_code = process.wait()

            # --- Post-Run Analysis ---
            # A non-zero exit code indicates a crash/error.
            if return_code != 0 and current_url:
                failure_counts[current_url] = failure_counts.get(current_url, 0) + 1
                count = failure_counts[current_url]
                full_error_log = "".join(output_buffer)

                print(f"\n--- Failure Detected ---")
                print(f"'{SCRIPT_TO_RUN}' stopped with error code {return_code} while processing:")
                print(f"URL: {current_url}")
                print(f"This URL has now failed {count}/{MAX_FAILURES} time(s).")
                
                if count >= MAX_FAILURES:
                    print(f"URL has reached the failure limit and will be removed.")
                    reason_summary = f"Failed {count} times. Last exit code: {return_code}."
                    log_removed_url(current_url, reason_summary, full_error_log)
                    if current_url not in urls_to_remove_this_run:
                        urls_to_remove_this_run.append(current_url)
                    # Remove from tracking to prevent re-adding
                    del failure_counts[current_url]
                print("----------------------")


            # --- File Modification (Happens during downtime) ---
            if urls_to_remove_this_run:
                print("\n--- URL Management (Post-Run) ---")
                remove_urls_from_list(urls_to_remove_this_run, URL_LIST_FILE)
                print("---------------------------------")

            if all_finished:
                print("Stopping the monitor as all downloads are finished.")
                break

            print("-" * 30)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] '{SCRIPT_TO_RUN}' has stopped.")
            print(f"Waiting for {WAIT_TIME_SECONDS} seconds before restarting...")
            
            time.sleep(WAIT_TIME_SECONDS)
            print("-" * 30)
        
        # --- Final Cleanup Check ---
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Monitor has finished its job.")
        
        if is_list_file_empty(URL_LIST_FILE):
            print(f"'{URL_LIST_FILE}' is empty. Commencing self-destruct sequence...")
            try:
                if os.path.isfile(URL_LIST_FILE):
                    print(f"Deleting '{URL_LIST_FILE}'...")
                    os.remove(URL_LIST_FILE)
                
                print(f"Deleting '{SCRIPT_TO_RUN}'...")
                os.remove(SCRIPT_TO_RUN)

                print(f"Deleting self ('{monitor_script_name}')... Goodbye!")
                os.remove(monitor_script_name)
            except OSError as e:
                print(f"\nError during self-destruct sequence: {e}")
                print("Cleanup may be incomplete.")
                sys.exit(1)
        else:
            print("List file is not empty. Exiting normally.")

        sys.exit(0)

    except KeyboardInterrupt:
        if 'urls_to_remove_this_run' in locals() and urls_to_remove_this_run:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] User interrupted. Removing successfully downloaded URLs from this session...")
            remove_urls_from_list(urls_to_remove_this_run, URL_LIST_FILE)
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Monitor stopped by user. Exiting.")
        sys.exit(0)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
