import subprocess
import time
import json

NS="bleater"
DEPLOY="bleater-frontend"
UID_FILE="/tmp/frontend-deploy-uid"

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except:
        return ""

def wait_ready():
    for _ in range(15):
        r = run(
            f"kubectl get deploy {DEPLOY} -n {NS} "
            "-o jsonpath='{.status.readyReplicas}'"
        )
        if r and r != "0":
            return True
        time.sleep(2)
    return False

def get_pod():
    return run(
        f"kubectl get pod -n {NS} -l app=frontend "
        "-o jsonpath='{.items[0].metadata.name}'"
    )

# -------------------------
# CHECK 1 — Binary validation
# -------------------------
pod = get_pod()

size = run(
    f"kubectl exec -n {NS} {pod} -- wc -c /app/app.wasm | awk '{{print $1}}'"
) if pod else "0"

check_binary = size.isdigit() and int(size) > 10000

# -------------------------
# CHECK 2 — Deployment ready
# -------------------------
check_ready = wait_ready()

# -------------------------
# CHECK 3 — UID preserved
# -------------------------
orig = run(f"cat {UID_FILE}")
curr = run(
    f"kubectl get deploy {DEPLOY} -n {NS} "
    "-o jsonpath='{.metadata.uid}'"
)

check_uid = orig == curr

# -------------------------
# CHECK 4 — LFS enabled TRUE
# -------------------------
envs = run(
    "kubectl get deploy argocd-repo-server -n argocd "
    "-o jsonpath='{.spec.template.spec.containers[0].env}'"
)

check_lfs = (
    "ARGOCD_GIT_LFS_ENABLED" in envs
    and "true" in envs
)

# -------------------------
# CHECK 5 — Service endpoints
# -------------------------
eps = run(
    f"kubectl get endpoints {DEPLOY} -n {NS} "
    "-o jsonpath='{.subsets}'"
)

check_eps = eps != ""

checks = [
    check_binary,
    check_ready,
    check_uid,
    check_lfs,
    check_eps,
]

result = {
    "score": sum(checks)/len(checks),
    "passed": sum(checks),
    "total": len(checks),
}

print(json.dumps(result))