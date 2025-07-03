# bandcamp-dump & Monitor

Original bandcamp-dump by [Grim Kriegor](https://github.com/GrimKriegor/dotfiles).

An automated script for downloading large public discographies from Bandcamp.

This project consists of two main components:

1.  `bandcamp-dump`: A Bash script that uses `bandcamp-dl` to download albums and tracks from a predefined list.
2.  `monitor.py`: A Python-based supervisor that runs `bandcamp-dump`, automatically retries failed downloads, removes successfully downloaded items from the queue, and logs problematic URLs.

## Features

* **Use a Local List (Recommended)**: Create your own list of Bandcamp URLs to download for maximum accuracy and reliability.
* **Resilient Downloads**: The monitor script ensures that if a download fails or the script crashes, it will be automatically restarted.
* **Failure Management**: Individual URLs that repeatedly fail to download are automatically removed from the queue and logged for manual review, preventing the entire process from getting stuck.
* **Smart Cleanup**: Successfully downloaded items are removed from the list, meaning you can stop and resume the process at any time without re-downloading anything.
* **Unique Naming**: Automatically extracts a unique ID for each album to prevent overwriting albums that might share the same name. **This is experimental, it retrieves a JSON from the source code and assumes the first integer to appear to be the item_id**
* **Automated Scraping (Not Recommended)**: The script has a legacy feature to scrape URLs from a Bandcamp page, but this is be unreliable.

## How It Works

The system is designed to be run via the `monitor.py` script for maximum reliability.

1.  **Initialization**: The `monitor.py` script starts the `bandcamp-dump` bash script.
2.  **URL List**: `bandcamp-dump` reads from the `bandcamp-dump.lst` file, which contains a list of album/track URLs, one per line.
3.  **Downloading**: The script processes one URL at a time, calling `bandcamp-dl` to perform the actual download.
4.  **Monitoring**: The `monitor.py` script watches the output of `bandcamp-dump` in real-time.
    * **On Success**: When an album is downloaded successfully, the monitor removes its URL from `bandcamp-dump.lst`.
    * **On Failure**: If the script exits with an error, the monitor logs the failure for that specific URL. If a URL fails too many times, it is removed from the list and logged to `removed.txt`.
5.  **Looping**: The monitor restarts the `bandcamp-dump` script if it returns an error (most likely being rate-limited). This continues until the `bandcamp-dump.lst` file is empty (everything has been downloaded).

## Prerequisites

You must have the following command-line tools installed.

* **Python 3**: For the monitor script.
* **`bandcamp-dl`**: The core utility for downloading.
    * Installation: `pip install bandcamp-dl`
* **`lynx`**: A text-based browser used for scraping URLs. (Only required for the unrecommended URL generation method)
    * On Ubuntu: `sudo apt-get install lynx`
* **`curl`**: Used for fetching page content. (Usually pre-installed)
* **`jq`**: A command-line JSON processor used for extracting metadata.
    * On Ubuntu: `sudo apt-get install jq`
* **`pup`**: A command-line HTML parser.
    * From source: https://github.com/ericchiang/pup

## Setup & Usage

### 1. Get the Scripts

Clone this repository or download the `bandcamp-dump` and `monitor.py` files into the same directory.

### 2. Create the URL List

You have two options for creating the `bandcamp-dump.lst` file.

**Option A: Create a Manual List (Recommended)**

This is the most reliable method. Create a file named `bandcamp-dump.lst` and paste in the full URLs of the albums or tracks you want to download, with one URL per line.

A great way to get these URLs is by using a browser extension like **[DATools for Firefox](https://github.com/jcomicsutils/discography-archive-tools)**, which can copy all links from a page.

```
https://someartist.bandcamp.com/album/album-one
https://anotherartist.bandcamp.com/track/a-cool-song
https://someartist.bandcamp.com/album/album-two

```

**Important**: Make sure your list has a blank line at the very end. If the last line of the file contains a URL, the script may skip it.

**Option B: Generate from a URL (Not Recommended)**

This method is unreliable. Run the `bandcamp-dump` script once, providing it with an artist's page Bandcamp URL.

```
bash bandcamp-dump https://someartist.bandcamp.com/
```

This will create a `bandcamp-dump.lst` file in the same directory, populated with all the album and track URLs found on that page **(unreliable)**.

### 3. Start the Monitor

Once you have your `bandcamp-dump.lst` file ready, start the monitor. It will begin the download process.

```
python3 monitor.py
```

The monitor will now run continuously, processing the list, handling failures, and restarting the script as needed. You can safely stop the monitor with `Ctrl+C` and restart it later; it will pick up where it left off.

All downloaded albums will appear in the same directory, organized by `Album Name [ID]`. You can change that by changing `--template` in `bandcamp-dump`, see [bandcamp-dl](https://github.com/iheanyi/bandcamp-dl) docs for details.

## Configuration

You can tweak the behavior of the monitor by editing the configuration variables at the top of the `monitor.py` file:

* `MAX_FAILURES`: The number of times a single URL can fail before it's removed from the queue. (Default: `5`)
* `WAIT_TIME_SECONDS`: The time in seconds the monitor waits after the script stops before restarting it. (Default: `60`)

## File Descriptions

* **`bandcamp-dump`**: The core Bash script that reads the URL list and executes `bandcamp-dl` for each item.
* **`monitor.py`**: The recommended way to run the downloader. This Python script provides resilience, state management, and logging.
* **`bandcamp-dump.lst`**: The queue of URLs to download. This file is modified by the scripts as they run.
* **`removed.txt`**: A log file that records which URLs were removed due to repeated failures, along with the error logs for diagnostics.