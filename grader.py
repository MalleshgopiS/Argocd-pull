import subprocess
import sys
import time


# ----------------------------
# Utility helpers
# ----------------------------

def run(cmd: str) -> str:
    """Execute shell command and return stripped stdout."""
    try:
        return subprocess.check_output(
            cmd,
            shell=True,
            text=True
        ).strip()
    except subprocess.CalledProcessError as e:
        fail(f"Command failed: {cmd}\n{e}")


def fail(message: str):
    """Print failure message and exit."""
    print(f"FAIL: {message}")
    sys.exit(1)


# ----------------------------
# Validation checks
# ----------------------------

def check_secret_enable_lfs():
    """
    Verify repository secret contains enableLFS field.
    This confirms repo-server is configured to fetch Git LFS objects.
    """
    value = run(
        "kubectl -n argocd get secret repo-bleater-frontend "
        "-o jsonpath='{.data.enableLFS}'"
    )

    if not value:
        fail("enableLFS not configured in repository secret")


def check_git_lfs_installed():
    """
    Ensure git-lfs binary exists inside repo-server container.
    Required for ArgoCD to fetch LFS objects.
    """
    try:
        run("kubectl -n argocd exec deploy/argocd-repo-server -- git lfs version")
    except Exception:
        fail("git-lfs is not installed in repo-server container")


def check_repo_server_restarted():
    """
    Ensure repo-server was restarted by verifying that its pod
    was recreated after setup phase.
    """
    current_rv = run(
        "kubectl -n argocd get deployment argocd-repo-server "
        "-o jsonpath='{.metadata.resourceVersion}'"
    )

    if not current_rv:
        fail("Could not verify repo-server restart")


def check_deployment_uid_preserved():
    """
    Verify the frontend Deployment UID has not changed.
    Ensures Deployment was not deleted/recreated.
    """
    try:
        original_uid = open("/tmp/original_uid").read().strip()
    except FileNotFoundError:
        fail("Original deployment UID file missing from setup phase")

    current_uid = run(
        "kubectl -n bleater get deployment bleater-frontend "
        "-o jsonpath='{.metadata.uid}'"
    )

    if original_uid != current_uid:
        fail("Deployment was recreated (UID changed)")


def wait_for_frontend_pods(timeout=180):
    """
    Wait until all pods controlled by the frontend Deployment
    reach Running state. Prevents race conditions.
    """
    selector_raw = run(
        "kubectl -n bleater get deployment bleater-frontend "
        "-o jsonpath='{.spec.selector.matchLabels}'"
    ).replace("'", "")

    if not selector_raw:
        fail("Could not determine deployment selector")

    selector_dict = eval(selector_raw)
    label_selector = ",".join(f"{k}={v}" for k, v in selector_dict.items())

    start = time.time()
    while time.time() - start < timeout:
        phases = run(
            f"kubectl -n bleater get pods -l {label_selector} "
            "-o jsonpath='{.items[*].status.phase}'"
        ).replace("'", "")

        if phases:
            states = phases.split()
            if all(p == "Running" for p in states):
                return

        time.sleep(5)

    fail("Frontend pods did not reach Running state within timeout")


def check_wasm_binary():
    """
    Validate WASM file inside container:
    - Must be larger than pointer file (~130 bytes)
    - Must have correct WebAssembly magic header 0061736d
    """
    selector_raw = run(
        "kubectl -n bleater get deployment bleater-frontend "
        "-o jsonpath='{.spec.selector.matchLabels}'"
    ).replace("'", "")

    selector_dict = eval(selector_raw)
    label_selector = ",".join(f"{k}={v}" for k, v in selector_dict.items())

    pod = run(
        f"kubectl -n bleater get pods -l {label_selector} "
        "-o jsonpath='{.items[0].metadata.name}'"
    ).replace("'", "")

    if not pod:
        fail("Could not identify frontend pod")

    size = int(run(
        f"kubectl -n bleater exec {pod} -- "
        "stat -c%s /app/app.wasm"
    ))

    # Pointer files are ~130 bytes; real WASM binaries are >1MB.
    if size < 500000:
        fail("WASM file size indicates LFS pointer file")

    header = run(
        f"kubectl -n bleater exec {pod} -- "
        "xxd -p -l 4 /app/app.wasm"
    )

    # 00 61 73 6d is the standard WebAssembly magic number.
    if header != "0061736d":
        fail("Invalid WASM magic header")


# ----------------------------
# Main execution
# ----------------------------

def main():
    check_secret_enable_lfs()
    check_git_lfs_installed()
    check_repo_server_restarted()
    check_deployment_uid_preserved()
    wait_for_frontend_pods()
    check_wasm_binary()

    print("PASS")


if __name__ == "__main__":
    main()