import subprocess
import sys
import time
import json


ARGO_NS = "argocd"
APP_NS = "bleater"
SECRET_NAME = "repo-bleater-platform"
APP_NAME = "bleater-platform"

WASM_PATH = "/app/app.wasm"
WASM_MIN_SIZE = 500000  # 500KB threshold to distinguish LFS pointer
WASM_MAGIC = "0061736d"  # Standard WebAssembly magic header


def run(cmd: str) -> str:
    """
    Execute a shell command and return stdout.
    Fail immediately if command fails.
    """
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except subprocess.CalledProcessError as e:
        fail(f"Command failed: {cmd}\n{e}")


def fail(message: str):
    """
    Print failure message and exit grading.
    """
    print(f"FAIL: {message}")
    sys.exit(1)


def get_frontend_deployment():
    """
    Dynamically discover the frontend deployment by:
    - Iterating through deployments in bleater namespace
    - Constructing selector from matchLabels using jq-safe JSON parsing
    - Checking for existence of /app/app.wasm in one of its pods
    """

    deployments_json = run(
        f"kubectl -n {APP_NS} get deployments -o json"
    )

    deployments = json.loads(deployments_json)["items"]

    for d in deployments:
        name = d["metadata"]["name"]
        labels = d["spec"]["selector"]["matchLabels"]

        if not labels:
            continue

        selector = ",".join([f"{k}={v}" for k, v in labels.items()])

        pods_json = run(
            f"kubectl -n {APP_NS} get pods -l {selector} -o json"
        )

        pods = json.loads(pods_json)["items"]

        if not pods:
            continue

        pod_name = pods[0]["metadata"]["name"]

        # Check if WASM file exists
        exists = subprocess.call(
            f"kubectl -n {APP_NS} exec {pod_name} -- test -f {WASM_PATH}",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if exists == 0:
            return name

    fail("Could not determine frontend deployment")


def check_secret_enable_lfs():
    """
    Verify repository secret contains enableLFS=true.
    """

    secret_json = run(
        f"kubectl -n {ARGO_NS} get secret {SECRET_NAME} -o json"
    )

    data = json.loads(secret_json).get("data", {})

    if "enableLFS" not in data:
        fail("enableLFS field missing in repository secret")

    decoded = subprocess.check_output(
        f"echo {data['enableLFS']} | base64 -d",
        shell=True,
        text=True
    ).strip()

    if decoded.lower() != "true":
        fail("enableLFS is not set to true")


def check_repo_server_restarted():
    """
    Ensure repo-server resourceVersion changed
    indicating rollout restart occurred.
    """

    original = open("/var/tmp/repo_server_rv").read().strip()

    current_json = run(
        f"kubectl -n {ARGO_NS} get deployment argocd-repo-server -o json"
    )

    current = json.loads(current_json)["metadata"]["resourceVersion"]

    if original == current:
        fail("repo-server was not restarted")


def check_deployment_uid_preserved():
    """
    Ensure frontend Deployment UID did not change.
    Prevents delete/recreate shortcuts.
    """

    deployment = get_frontend_deployment()

    original = open("/var/tmp/original_uid").read().strip()

    deployment_json = run(
        f"kubectl -n {APP_NS} get deployment {deployment} -o json"
    )

    current = json.loads(deployment_json)["metadata"]["uid"]

    if original != current:
        fail("Deployment UID changed (should not recreate deployment)")


def wait_for_frontend_pods(timeout=180):
    """
    Wait until all frontend pods are Running.
    Poll every 5 seconds up to timeout.
    """

    deployment = get_frontend_deployment()

    deployment_json = run(
        f"kubectl -n {APP_NS} get deployment {deployment} -o json"
    )

    labels = json.loads(deployment_json)["spec"]["selector"]["matchLabels"]
    selector = ",".join([f"{k}={v}" for k, v in labels.items()])

    start = time.time()

    while time.time() - start < timeout:

        pods_json = run(
            f"kubectl -n {APP_NS} get pods -l {selector} -o json"
        )

        pods = json.loads(pods_json)["items"]

        if not pods:
            time.sleep(5)
            continue

        phases = [p["status"]["phase"] for p in pods]

        if all(p == "Running" for p in phases):
            return

        time.sleep(5)

    fail("Frontend pods did not reach Running state within timeout")


def check_wasm_binary():
    """
    Validate WASM binary inside frontend pod:
    - File size must exceed WASM_MIN_SIZE
    - First 4 bytes must equal WASM_MAGIC
    """

    deployment = get_frontend_deployment()

    deployment_json = run(
        f"kubectl -n {APP_NS} get deployment {deployment} -o json"
    )

    labels = json.loads(deployment_json)["spec"]["selector"]["matchLabels"]
    selector = ",".join([f"{k}={v}" for k, v in labels.items()])

    pods_json = run(
        f"kubectl -n {APP_NS} get pods -l {selector} -o json"
    )

    pod_name = json.loads(pods_json)["items"][0]["metadata"]["name"]

    size = int(run(
        f"kubectl -n {APP_NS} exec {pod_name} -- stat -c%s {WASM_PATH}"
    ))

    if size < WASM_MIN_SIZE:
        fail("WASM file size indicates LFS pointer instead of binary")

    header = run(
        f"kubectl -n {APP_NS} exec {pod_name} -- xxd -p -l 4 {WASM_PATH}"
    )

    if header != WASM_MAGIC:
        fail("Invalid WASM magic header")


def main():
    check_secret_enable_lfs()
    check_repo_server_restarted()
    check_deployment_uid_preserved()
    wait_for_frontend_pods()
    check_wasm_binary()
    print("PASS")


if __name__ == "__main__":
    main()