import subprocess
import sys
import time


def run(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except subprocess.CalledProcessError as e:
        fail(f"Command failed: {cmd}\n{e}")


def fail(message: str):
    print(f"FAIL: {message}")
    sys.exit(1)


def get_frontend_deployment():
    for d in run("kubectl -n bleater get deployments -o jsonpath='{.items[*].metadata.name}'").replace("'", "").split():
        pods = run(f"kubectl -n bleater get pods --selector=app={d} -o jsonpath='{{.items[*].metadata.name}}'").replace("'", "")
        if pods:
            pod = pods.split()[0]
            if subprocess.call(f"kubectl -n bleater exec {pod} -- test -f /app/app.wasm", shell=True) == 0:
                return d
    fail("Could not determine frontend deployment")


def check_secret_enable_lfs():
    value = run("kubectl -n argocd get secret repo-bleater-platform -o jsonpath='{.data.enableLFS}'").replace("'", "")
    if not value:
        fail("enableLFS missing in repository secret")

    decoded = run("kubectl -n argocd get secret repo-bleater-platform -o jsonpath='{.data.enableLFS}' | base64 -d")
    if decoded.lower() != "true":
        fail("enableLFS not set to true")


def check_repo_server_restarted():
    original = open("/var/tmp/repo_server_rv").read().strip()
    current = run("kubectl -n argocd get deployment argocd-repo-server -o jsonpath='{.metadata.resourceVersion}'")
    if original == current:
        fail("repo-server was not restarted")


def check_deployment_uid_preserved():
    deployment = get_frontend_deployment()
    original = open("/var/tmp/original_uid").read().strip()
    current = run(f"kubectl -n bleater get deployment {deployment} -o jsonpath='{{.metadata.uid}}'")
    if original != current:
        fail("Deployment UID changed")


def wait_for_frontend_pods(timeout=180):
    deployment = get_frontend_deployment()
    selector = run(
        f"kubectl -n bleater get deployment {deployment} "
        "-o jsonpath='{range $k,$v := .spec.selector.matchLabels}{$k}={$v},{{end}}'"
    ).replace("'", "").rstrip(",")

    start = time.time()
    while time.time() - start < timeout:
        phases = run(f"kubectl -n bleater get pods -l {selector} -o jsonpath='{{.items[*].status.phase}}'").replace("'", "")
        if phases and all(p == "Running" for p in phases.split()):
            return
        time.sleep(5)

    fail("Frontend pods did not reach Running state")


def check_wasm_binary():
    deployment = get_frontend_deployment()
    selector = run(
        f"kubectl -n bleater get deployment {deployment} "
        "-o jsonpath='{range $k,$v := .spec.selector.matchLabels}{$k}={$v},{{end}}'"
    ).replace("'", "").rstrip(",")

    pod = run(f"kubectl -n bleater get pods -l {selector} -o jsonpath='{{.items[0].metadata.name}}'").replace("'", "")

    size = int(run(f"kubectl -n bleater exec {pod} -- stat -c%s /app/app.wasm"))
    if size < 500000:
        fail("WASM file size indicates LFS pointer")

    header = run(f"kubectl -n bleater exec {pod} -- xxd -p -l 4 /app/app.wasm")
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