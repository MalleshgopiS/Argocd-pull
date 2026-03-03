import subprocess
import sys


def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()


def fail(message):
    print(f"FAIL: {message}")
    sys.exit(1)


def check_lfs_enabled():
    output = run("kubectl -n argocd get secret repo-bleater-frontend -o yaml")
    if 'enableLFS: "true"' not in output:
        fail("Git LFS not enabled in repository secret")


def check_git_lfs_installed():
    try:
        run("kubectl -n argocd exec deploy/argocd-repo-server -- git lfs version")
    except subprocess.CalledProcessError:
        fail("git-lfs not available in repo-server container")


def get_frontend_pod():
    pods = run("kubectl get pods -n bleater -o jsonpath='{.items[0].metadata.name}'")
    if not pods:
        fail("No frontend pod found")
    return pods.strip("'")


def check_pod_running():
    output = run("kubectl get pods -n bleater --no-headers")
    if "Running" not in output:
        fail("Frontend pod is not running")


def check_wasm_binary():
    pod = get_frontend_pod()

    # Check file size
    size = run(f"kubectl exec -n bleater {pod} -- stat -c%s /app/app.wasm")
    if int(size) < 1000000:
        fail("WASM file too small (likely LFS pointer file)")

    # Check magic header
    header = run(f"kubectl exec -n bleater {pod} -- xxd -p -l 4 /app/app.wasm")
    if header != "0061736d":
        fail("Invalid WASM magic header")

    # Ensure pointer text not present
    content_check = run(f"kubectl exec -n bleater {pod} -- head -n 1 /app/app.wasm || true")
    if "git-lfs.github.com" in content_check:
        fail("LFS pointer file still present")


def main():
    check_lfs_enabled()
    check_git_lfs_installed()
    check_pod_running()
    check_wasm_binary()

    print("PASS: All validation checks successful")


if __name__ == "__main__":
    main()