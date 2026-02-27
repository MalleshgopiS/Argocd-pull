import subprocess
import time
import json

NS = "bleater"
DEPLOY = "bleater-frontend"
ARGO_NS = "argocd"

UID_FILE = "/grader/frontend-deploy-uid"


def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except:
        return ""


def wait_ready():
    for _ in range(20):
        ready = run(
            f"kubectl get deploy {DEPLOY} -n {NS} "
            "-o jsonpath='{.status.readyReplicas}'"
        )
        if ready and ready != "0":
            return True
        time.sleep(2)
    return False


def get_running_pod():
    return run(
        f"kubectl get pods -n {NS} -l app=frontend "
        "-o jsonpath='{.items[?(@.status.phase==\"Running\")].metadata.name}'"
    )


# CHECK 1 — WASM not LFS pointer
pod = get_running_pod()
check_binary = False

if pod:
    wasm = run(
        f"kubectl exec -n {NS} {pod} -- cat /app/app.wasm"
    )
    check_binary = "git-lfs.github.com/spec" not in wasm


# CHECK 2 — Deployment ready
check_ready = wait_ready()


# CHECK 3 — UID preserved
orig_uid = run(f"cat {UID_FILE}")
curr_uid = run(
    f"kubectl get deploy {DEPLOY} -n {NS} "
    "-o jsonpath='{.metadata.uid}'"
)
check_uid = orig_uid == curr_uid


# CHECK 4 — LFS enabled EXACT
lfs_val = run(
    "kubectl get deploy argocd-repo-server -n argocd "
    "-o jsonpath='{.spec.template.spec.containers[0].env"
    "[?(@.name==\"ARGOCD_GIT_LFS_ENABLED\")].value}'"
)

check_lfs = lfs_val == "true"


# CHECK 5 — Service endpoints
eps = run(
    f"kubectl get endpoints {DEPLOY} -n {NS} "
    "-o jsonpath='{.subsets}'"
)

check_eps = eps not in ("", "[]", "<no value>")


checks = [
    check_binary,
    check_ready,
    check_uid,
    check_lfs,
    check_eps,
]

score = sum(checks) / len(checks)

print(json.dumps({
    "score": score,
    "passed": sum(checks),
    "total": len(checks)
}))