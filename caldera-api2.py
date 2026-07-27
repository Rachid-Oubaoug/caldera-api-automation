import requests
import urllib3
import uuid
import time
import os
import sys
from datetime import datetime, timedelta

# === Config ===
# Environment variables ensure secrets are not committed to source control
CALDERA_URL = os.getenv('CALDERA_URL', 'https://your-caldera-instance.com')
CERT_FILE = os.getenv('CERT_FILE', 'client.crt')
KEY_FILE = os.getenv('KEY_FILE', 'client.key')
SESSION_COOKIE = os.getenv('CALDERA_SESSION_COOKIE', '')

if not SESSION_COOKIE:
    print("[-] Error: CALDERA_SESSION_COOKIE environment variable is not set.")
    sys.exit(1)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

cookies = {
    'API_SESSION': SESSION_COOKIE
}

# === Functions ===

def list_operations():
    response = requests.get(
        f'{CALDERA_URL}/api/v2/operations',
        cert=(CERT_FILE, KEY_FILE),
        cookies=cookies,
        verify=False
    )
    response.raise_for_status()
    return response.json()

def list_alive_agents():
    response = requests.get(
        f'{CALDERA_URL}/api/v2/agents',
        cert=(CERT_FILE, KEY_FILE),
        cookies=cookies,
        verify=False
    )
    response.raise_for_status()
    agents = response.json()

    alive_agents = []
    now = datetime.utcnow()

    for agent in agents:
        last_seen_str = agent.get("last_seen")
        if last_seen_str:
            try:
                last_seen = datetime.strptime(last_seen_str, "%Y-%m-%dT%H:%M:%SZ")
                is_recent = (now - last_seen) < timedelta(minutes=10)
            except Exception:
                is_recent = True  
        else:
            is_recent = True

        if agent.get("pending_contact") and is_recent:
            alive_agents.append(agent)

    return alive_agents

def create_temp_ability(command, executor='sh'):
    ability_id = str(uuid.uuid4())
    platform = 'linux' if executor == 'sh' else 'windows'

    full_ability = {
        "ability_id": ability_id,
        "name": "Manual Command via API",
        "tactic": "execution",
        "technique_id": "T1059",
        "technique_name": "Command and Scripting Interpreter",
        "plugin": "stockpile",
        "description": f"Run '{command}' via temporary ability",
        "executors": [{
            "name": executor,
            "command": command,
            "platform": platform,
            "timeout": 60
        }]
    }

    response = requests.post(
        f'{CALDERA_URL}/api/v2/abilities',
        cert=(CERT_FILE, KEY_FILE),
        cookies=cookies,
        json=full_ability,
        verify=False
    )
    response.raise_for_status()
    return full_ability

def assign_command_link(operation_id, paw, full_ability, executor='sh'):
    executor_obj = {
        "name": executor,
        "platform": "linux" if executor == "sh" else "windows",
        "command": full_ability["executors"][0]["command"],
        "timeout": full_ability["executors"][0].get("timeout", 60)
    }

    payload = {
        "paw": paw,
        "executor": executor_obj,
        "ability": full_ability
    }

    response = requests.post(
        f'{CALDERA_URL}/api/v2/operations/{operation_id}/potential-links',
        cert=(CERT_FILE, KEY_FILE),
        cookies=cookies,
        json=payload,
        verify=False
    )
    if not response.ok:
        print("⚠️ Full error response from server:")
        print(response.text)
    response.raise_for_status()
    return response.json()

def wait_for_command_status_in_operation(operation_id, paw, ability_id, timeout=90, interval=5):
    print("[*] Monitoring command status from operation log...")
    start_time = time.time()
    last_printed_status = None
    last_status_code = None

    while True:
        elapsed = int(time.time() - start_time)
        if elapsed > timeout:
            print("\n⏰ Timeout reached. No final status.")
            return "⚠️ Timed out", "No output"

        try:
            response = requests.get(
                f'{CALDERA_URL}/api/v2/operations/{operation_id}',
                cert=(CERT_FILE, KEY_FILE),
                cookies=cookies,
                verify=False
            )
            response.raise_for_status()
            operation = response.json()

            chain = operation.get("chain", [])
            matching_links = [
                link for link in chain
                if link.get("paw") == paw and link.get("ability", {}).get("ability_id") == ability_id
            ]

            if not matching_links:
                msg = f"  ⏳ [{elapsed}s] Waiting for command to register in operation..."
                if msg != last_printed_status:
                    print(msg)
                    last_printed_status = msg
            else:
                link = sorted(matching_links, key=lambda l: l.get("collect", ""), reverse=True)[0]
                status = link.get("status")
                output_flag = link.get("output", "False")
                finish = link.get("finish", "—")

                status_map = {
                    0: "✅ Success",
                    -1: "❌ Failed",
                    -3: "❗ Not executed",
                    1: "⏳ Running"
                }
                status_msg = status_map.get(status, f"❓ Unknown ({status})")
                line = f"  ⏳ [{elapsed}s] Status: {status_msg} | Output: {output_flag} | Finish: {finish}"

                if status == -3:
                    sys.stdout.write(f"\r{line}")
                    sys.stdout.flush()
                else:
                    if status != last_status_code:
                        print(f"\n{line}")
                        last_status_code = status

                if status in [0, -1]:
                    return status_msg, output_flag

        except Exception as e:
            print(f"\n  ⚠️ Error during polling: {e}")

        time.sleep(interval)

# === Main ===

if __name__ == '__main__':
    try:
        print("[*] Fetching operations...")
        operations = list_operations()
        for idx, op in enumerate(operations):
            print(f"{idx + 1}. {op['name']} (ID: {op['id']})")

        op_index = int(input("Select operation number: ")) - 1
        operation_id = operations[op_index]['id']

        print("\n[*] Fetching alive agents...")
        agents = list_alive_agents()
        if not agents:
            raise RuntimeError("No alive agents found.")

        for idx, agent in enumerate(agents):
            trust = "✅" if agent.get("trusted") else "⚠️"
            print(f"{idx + 1}. {agent['paw']} ({agent['platform']}) {trust} — last seen: {agent.get('last_seen')}")

        agent_index = int(input("Select agent number: ")) - 1
        selected_agent = agents[agent_index]
        paw = selected_agent['paw']
        available_executors = selected_agent.get('executors', [])

        if not available_executors:
            raise RuntimeError(f"No executors available for agent {paw}.")

        print(f"Available executors: {available_executors}")
        executor = input(f"Choose executor to use (default: {available_executors[0]}): ") or available_executors[0]

        command = input("Enter the manual command to execute: ")

        print(f"[*] Creating temporary ability for: {command}")
        full_ability = create_temp_ability(command, executor=executor)

        print("[*] Waiting briefly to ensure ability registration...")
        time.sleep(2)

        print(f"[*] Assigning command to agent {paw} in operation {operation_id}...")
        result = assign_command_link(operation_id, paw, full_ability, executor=executor)

        print("[+] Command dispatched successfully!")
        print("Response:")
        print(result)

        status_msg, output_flag = wait_for_command_status_in_operation(
            operation_id,
            paw,
            full_ability["ability_id"]
        )

        print(f"\n📊 Final Command Status: {status_msg}")
        print(f"📤 Output Available: {output_flag}")

    except Exception as e:
        print("[-] Error:", e)
