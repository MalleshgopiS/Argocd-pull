import subprocess
import sys
import time
import json

ARGO_NS = "argocd"
APP_NS = "bleater"
SECRET_NAME = "repo-bleater-platform"
APP_NAME = "bleater-platform"

# Correct Nebula frontend WASM location
WASM_PATH = "/usr/share/nginx/html/app.wasm"

WASM_MIN_SIZE = 500000  # 500KB threshold
WASM_MAGIC = "0061736d"  # WebAssembly magic header


def run(cmd: str) -> str:
    """Execute shell command and return stdout."""
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except subprocess.CalledProcessError as e:
        fail(f"Command failed: {cmd}\n{e}")


def fail(message: str):
    """Fail grading immediately."""
    print(f"FAIL: {message}")
    sys.exit(1)


def get_frontend_deployment():
    """
    Determine frontend deployment using stable Nebula label:
    app.kubernetes.io/name=bleater-frontend
    """
    deployment = run(
        f"kubectl -n {APP_NS} get deployment "
        f"-l app.kubernetes.io/name=bleater-frontend "
        f"-o json | jq -r '.items[0].metadata.name'"
    )

    if not deployment or deployment == "null":
        fail("Could not determine frontend deployment")

    return deployment


def get_frontend_selector():
    """Build label selector from deployment matchLabels."""
    deployment = get_frontend_deployment()

    deployment_json = run(
        f"kubectl -n {APP_NS} get deployment {deployment} -o json"
    )

    labels = json.loads(deployment_json)["spec"]["selector"]["matchLabels"]

    return ",".join([f"{k}={v}" for k, v in labels.items()])


def get_frontend_pod():
    """Return first frontend pod."""
    selector = get_frontend_selector()

    pods_json = run(
        f"kubectl -n {APP_NS} get pods -l {selector} -o json"
    )

    pods = json.loads(pods_json)["items"]

    if not pods:
        fail("No frontend pods found")

    return pods[0]["metadata"]["name"]


# ---------------------------------------------------------
# Checks
# ---------------------------------------------------------

def check_secret_enable_lfs():
    """Verify repository secret contains enableLFS=true."""
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
    Verify repo-server deployment resourceVersion changed,
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
    Ensure frontend Deployment UID has not changed.
    Prevents delete/recreate shortcut.
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
    selector = get_frontend_selector()

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
    - First 4 bytes must match WASM_MAGIC
    """
    pod = get_frontend_pod()

    size = int(run(
        f"kubectl -n {APP_NS} exec {pod} -- stat -c%s {WASM_PATH}"
    ))

    if size < WASM_MIN_SIZE:
        fail("WASM file size indicates LFS pointer instead of binary")

    header = run(
        f"kubectl -n {APP_NS} exec {pod} -- xxd -p -l 4 {WASM_PATH}"
    )

    if header != WASM_MAGIC:
        fail("Invalid WASM magic header")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    check_secret_enable_lfs()
    check_repo_server_restarted()
    check_deployment_uid_preserved()
    wait_for_frontend_pods()
    check_wasm_binary()
    print("PASS")


if __name__ == "__main__":
    main()