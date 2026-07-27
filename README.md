# MITRE Caldera API Automation

This repository contains a Python automation script (`caldera-api2.py`) designed to interact with the MITRE Caldera API. It allows users to dynamically select active operations, find alive agents, and execute temporary commands on the fly.

## Features

*   **List Operations:** Automatically fetches and lists available operations.
*   **Identify Alive Agents:** Filters agents to find those that have checked in recently (within 10 minutes).
*   **Dynamic Command Execution:** Creates a temporary ability and dispatches it to a selected agent.
*   **Live Monitoring:** Polls the operation log to return the success/failure status of your dispatched command.

## Prerequisites

*   Python 3.x
*   `requests` and `urllib3` libraries

You can install the required libraries using:

```bash
pip install requests urllib3
```

## Configuration

For security reasons, this script uses environment variables instead of hardcoded credentials. You must set the following variables before running the script:

*   `CALDERA_URL`: The base URL of your Caldera instance (e.g., `[https://your-caldera-instance.com](https://your-caldera-instance.com)`).
*   `CERT_FILE`: Path to your client certificate (e.g., `client.crt`).
*   `KEY_FILE`: Path to your client key (e.g., `client.key`).
*   `CALDERA_SESSION_COOKIE`: Your active API session cookie.

**Example Setup (Linux/macOS):**

```bash
export CALDERA_URL="https://your-instance.com:8443"
export CERT_FILE="./my-caldera.crt"
export KEY_FILE="./my-caldera.key"
export CALDERA_SESSION_COOKIE="gAAAAAB..."
```

## Usage

Once your environment variables are configured, simply run the script:

```bash
python caldera-api2.py
```

Follow the interactive terminal prompts to select your operation, choose an agent, and input the command you wish to execute.
