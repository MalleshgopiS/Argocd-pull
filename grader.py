import subprocess
import sys
import time


def run(cmd: str) -> str:
    """Execute shell command and return output."""
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except subprocess.CalledProcessError as e:
        fail(f"Command failed: {cmd}\n{e}")


def fail(message: str):
    """Exit grading with failure."""
    print(f"FAIL: {message}")
    sys.exit(1)


def get_frontend_deployment():
    """
    Dynamically discover the frontend deployment by:
    - Iterating through all deployments in bleater namespace
    - Using actual matchLabels selector
    - Checking for existence of /app/app.wasm
    """
    deployments = run(
        "kubectl -n bleater get deployments -o jsonpath='{.items[*].metadata.name}'"
    ).replace("'", "").split()

    for d in deployments:
        selector = run(
            f"kubectl -n bleater get deployment {d} "
            "-o jsonpath='{range $k,$v := .spec.selector.matchLabels}{$k}={$v},{{end}}'"
        ).replace("'", "").rstrip(",")

        if not selector:
            continue

        pods = run(
            f"kubectl -n bleater get pods -l {selector} "
            "-o jsonpath='{.items[*].metadata.name}'"
        ).replace("'", "")

        if not pods:
            continue

        pod = pods.split()[0]

        if subprocess.call(
            f"kubectl -n bleater exec {pod} -- test -f /app/app.wasm",
            shell=True,
        ) == 0:
            return d

    fail("Could not determine frontend deployment")


def check_secret_enable_lfs():
    """Verify repository secret contains enableLFS=true."""
    encoded = run(
        "kubectl -n argocd get secret repo-bleater-platform "
        "-o jsonpath='{.data.enableLFS}'"
    ).replace("'", "")

    if not encoded:
        fail("enableLFS missing in repository secret")

    decoded = subprocess.check_output(
        f"echo {encoded} | base64 -d", shell=True, text=True
    ).strip()

    if decoded.lower() != "true":
        fail("enableLFS is not set to true")


def check_repo_server_restarted():
    """Ensure repo-server resourceVersion changed."""
    original = open("/var/tmp/repo_server_rv").read().strip()
    current = run(
        "kubectl -n argocd get deployment argocd-repo-server "
        "-o jsonpath='{.metadata.resourceVersion}'"
    ).replace("'", "")

    if original == current:
        fail("repo-server was not restarted")


def check_deployment_uid_preserved():
    """Ensure frontend Deployment UID did not change."""
    deployment = get_frontend_deployment()
    original = open("/var/tmp/original_uid").read().strip()
    current = run(
        f"kubectl -n bleater get deployment {deployment} "
        "-o jsonpath='{.metadata.uid}'"
    ).replace("'", "")

    if original != current:
        fail("Deployment UID changed (should not recreate)")


def wait_for_frontend_pods(timeout=180):
    """Wait until all frontend pods are Running."""
    deployment = get_frontend_deployment()

    selector = run(
        f"kubectl -n bleater get deployment {deployment} "
        "-o jsonpath='{range $k,$v := .spec.selector.matchLabels}{$k}={$v},{{end}}'"
    ).replace("'", "").rstrip(",")

    start = time.time()

    while time.time() - start < timeout:
        phases = run(
            f"kubectl -n bleater get pods -l {selector} "
            "-o jsonpath='{.items[*].status.phase}'"
        ).replace("'", "")

        if phases and all(p == "Running" for p in phases.split()):
            return

        time.sleep(5)

    fail("Frontend pods did not reach Running state")


def check_wasm_binary():
    """
    Validate WASM:
    - Size must be > 500KB (pointer files are tiny)
    - Magic header must equal 0061736d
    """
    deployment = get_frontend_deployment()

    selector = run(
        f"kubectl -n bleater get deployment {deployment} "
        "-o jsonpath='{range $k,$v := .spec.selector.matchLabels}{$k}={$v},{{end}}'"
    ).replace("'", "").rstrip(",")

    pod = run(
        f"kubectl -n bleater get pods -l {selector} "
        "-o jsonpath='{.items[0].metadata.name}'"
    ).replace("'", "")

    size = int(run(
        f"kubectl -n bleater exec {pod} -- stat -c%s /app/app.wasm"
    ))

    if size < 500000:
        fail("WASM file size indicates LFS pointer")

    header = run(
        f"kubectl -n bleater exec {pod} -- xxd -p -l 4 /app/app.wasm"
    )

    if header != "0061736d":
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