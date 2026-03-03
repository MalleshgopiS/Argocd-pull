import subprocess
import sys
import time


def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def wait_for_pods(namespace, label_selector, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        output = run(
            f"kubectl get pods -n {namespace} -l {label_selector} "
            "-o jsonpath='{.items[*].status.phase}'"
        ).replace("'", "")
        if output and all(p == "Running" for p in output.split()):
            return
        time.sleep(5)
    fail("Pods did not reach Running state in time")


def check_secret():
    output = run(
        "kubectl -n argocd get secret repo-bleater-frontend "
        "-o jsonpath='{.data.enableLFS}'"
    )
    if not output:
        fail("enableLFS not set in repository secret")


def check_git_lfs():
    try:
        run("kubectl -n argocd exec deploy/argocd-repo-server -- git lfs version")
    except subprocess.CalledProcessError:
        fail("git-lfs not installed in repo-server")


def check_uid_preserved():
    original = open("/tmp/original_uid").read().strip()
    current = run(
        "kubectl -n bleater get deployment bleater-frontend "
        "-o jsonpath='{.metadata.uid}'"
    )
    if original != current:
        fail("Deployment was recreated (UID changed)")


def check_wasm():
    pod = run(
        "kubectl get pods -n bleater "
        "-l app=bleater-frontend "
        "-o jsonpath='{.items[0].metadata.name}'"
    ).replace("'", "")

    size = int(run(
        f"kubectl exec -n bleater {pod} -- "
        "stat -c%s /app/app.wasm"
    ))

    # Pointer files are ~130 bytes; real WASM > 1MB
    if size < 500000:
        fail("WASM file size indicates pointer file")

    header = run(
        f"kubectl exec -n bleater {pod} -- "
        "xxd -p -l 4 /app/app.wasm"
    )

    if header != "0061736d":
        fail("Invalid WASM magic header")


def main():
    check_secret()
    check_git_lfs()
    check_uid_preserved()
    wait_for_pods("bleater", "app=bleater-frontend")
    check_wasm()
    print("PASS")


if __name__ == "__main__":
    main()