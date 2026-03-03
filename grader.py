import subprocess
import sys
import time


# ----------------------------
# Utility Helpers
# ----------------------------

def run(cmd: str) -> str:
    """
    Execute shell command and return stripped stdout.
    Fail cleanly if command errors.
    """
    try:
        return subprocess.check_output(
            cmd,
            shell=True,
            text=True
        ).strip()
    except subprocess.CalledProcessError as e:
        fail(f"Command failed: {cmd}\n{e}")


def fail(message: str):
    """
    Print failure message and exit immediately.
    """
    print(f"FAIL: {message}")
    sys.exit(1)


# ----------------------------
# Core Validation Checks
# ----------------------------

def get_frontend_deployment():
    """
    Dynamically discover frontend Deployment using ArgoCD instance label.
    Avoids hardcoding deployment name.
    """
    deployment = run(
        "kubectl -n bleater get deployments "
        "-o jsonpath='{.items[?(@.metadata.labels.app\\.kubernetes\\.io/instance==\"bleater-frontend\")].metadata.name}'"
    ).replace("'", "")

    if not deployment:
        fail("Could not discover frontend Deployment")

    return deployment


def check_secret_enable_lfs():
    """
    Ensure repository secret explicitly sets enableLFS=true.
    """
    value = run(
        "kubectl -n argocd get secret repo-bleater-frontend "
        "-o jsonpath='{.data.enableLFS}'"
    ).replace("'", "")

    if not value:
        fail("enableLFS field missing in repository secret")

    # value is base64 encoded
    decoded = run(
        "kubectl -n argocd get secret repo-bleater-frontend "
        "-o jsonpath='{.data.enableLFS}' | base64 -d"
    )

    if decoded.lower() != "true":
        fail("enableLFS is not set to 'true'")


def check_git_lfs_installed():
    """
    Verify git-lfs binary exists in repo-server container.
    """
    try:
        run("kubectl -n argocd exec deploy/argocd-repo-server -- git lfs version")
    except Exception:
        fail("git-lfs not available in repo-server container")


def check_repo_server_restarted():
    """
    Verify repo-server Deployment resourceVersion changed
    after setup phase.
    """
    try:
        original_rv = open("/var/tmp/repo_server_rv").read().strip()
    except FileNotFoundError:
        fail("Original repo-server resourceVersion not recorded in setup")

    current_rv = run(
        "kubectl -n argocd get deployment argocd-repo-server "
        "-o jsonpath='{.metadata.resourceVersion}'"
    )

    if original_rv == current_rv:
        fail("repo-server was not restarted")


def check_deployment_uid_preserved():
    """
    Ensure frontend Deployment was NOT deleted/recreated.
    """
    deployment = get_frontend_deployment()

    try:
        original_uid = open("/var/tmp/original_uid").read().strip()
    except FileNotFoundError:
        fail("Original Deployment UID file missing")

    current_uid = run(
        f"kubectl -n bleater get deployment {deployment} "
        "-o jsonpath='{.metadata.uid}'"
    )

    if original_uid != current_uid:
        fail("Deployment was recreated (UID changed)")


def wait_for_frontend_pods(timeout=180):
    """
    Wait until all frontend pods reach Running state.
    Prevents race conditions.
    """
    deployment = get_frontend_deployment()

    label_selector = run(
        f"kubectl -n bleater get deployment {deployment} "
        "-o jsonpath='{range $k,$v := .spec.selector.matchLabels}{$k}={$v},{{end}}'"
    ).replace("'", "").rstrip(",")

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
    Validate deployed WASM file:
    - Size must exceed pointer file size (~130 bytes)
    - Must contain valid WebAssembly magic header 0061736d
    """
    deployment = get_frontend_deployment()

    label_selector = run(
        f"kubectl -n bleater get deployment {deployment} "
        "-o jsonpath='{range $k,$v := .spec.selector.matchLabels}{$k}={$v},{{end}}'"
    ).replace("'", "").rstrip(",")

    pod = run(
        f"kubectl -n bleater get pods -l {label_selector} "
        "-o jsonpath='{.items[0].metadata.name}'"
    ).replace("'", "")

    if not pod:
        fail("Could not determine frontend pod")

    size = int(run(
        f"kubectl -n bleater exec {pod} -- stat -c%s /app/app.wasm"
    ))

    # Pointer files are ~130 bytes; real WASM binaries are >1MB.
    if size < 500000:
        fail("WASM file size indicates LFS pointer file")

    header = run(
        f"kubectl -n bleater exec {pod} -- xxd -p -l 4 /app/app.wasm"
    )

    if header != "0061736d":
        fail("Invalid WASM magic header")


# ----------------------------
# Main Execution
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