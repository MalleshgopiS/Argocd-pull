#!/usr/bin/env python3

"""
Grader — ArgoCD Git LFS Broken

This grader validates that the ArgoCD Git LFS configuration issue
has been correctly resolved by the agent.

Validation Overview
-------------------
The grader performs five independent checks against live Kubernetes
cluster state:

1. WASM Binary Validation
   Ensures the deployed app.wasm file is NOT a Git LFS pointer file.

2. Deployment Readiness
   Confirms the frontend deployment becomes Ready.

3. Deployment UID Preservation
   Ensures the deployment resource was patched rather than deleted
   and recreated by comparing the UID saved during setup.

4. ArgoCD Git LFS Configuration
   Verifies that Git LFS support is enabled in the argocd-repo-server
   deployment via environment variable configuration.

5. Service Endpoint Restoration
   Confirms Kubernetes service endpoints are restored, meaning
   traffic routing is functional again.

Scoring
-------
Final score = passed_checks / total_checks

The grader relies entirely on live Kubernetes state and does not
inspect solution steps, preventing shortcut-based solutions.
"""

import subprocess
import json
import time

NS = "bleater"
DEPLOY = "bleater-frontend"
UID_FILE = "/grader/frontend-deploy-uid"


def run(cmd: str) -> str:
    """
    Execute a shell command and return stdout.

    Any execution error returns an empty string instead of raising
    an exception to keep grading deterministic.
    """
    try:
        return subprocess.check_output(
            cmd, shell=True, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def wait_ready():
    """
    Wait for the frontend deployment to report Ready replicas.

    Polls Kubernetes for up to ~40 seconds to allow rollout and
    reconciliation to complete.
    """
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
    """
    Return the name of a running frontend pod.

    Uses label selection and running phase filtering.
    Returns empty string if no pod is available.
    """
    return run(
        f"kubectl get pods -n {NS} "
        "-l app=frontend "
        "-o jsonpath='{.items[?(@.status.phase==\"Running\")].metadata.name}'"
    )


# ------------------------------------------------------------
# CHECK 1 — WASM not LFS pointer
# ------------------------------------------------------------
pod = get_running_pod()

if not pod:
    check_binary = False
else:
    wasm = run(
        f"kubectl exec -n {NS} {pod} -- "
        "cat /app/app.wasm 2>/dev/null || true"
    )
    check_binary = "git-lfs.github.com/spec" not in wasm


# ------------------------------------------------------------
# CHECK 2 — Deployment Ready
# ------------------------------------------------------------
check_ready = wait_ready()


# ------------------------------------------------------------
# CHECK 3 — UID preserved
# ------------------------------------------------------------
orig_uid = ""
try:
    with open(UID_FILE) as f:
        orig_uid = f.read().strip()
except Exception:
    orig_uid = ""

curr_uid = run(
    f"kubectl get deploy {DEPLOY} -n {NS} "
    "-o jsonpath='{.metadata.uid}'"
)

check_uid = orig_uid != "" and orig_uid == curr_uid


# ------------------------------------------------------------
# CHECK 4 — LFS enabled EXACT value
# ------------------------------------------------------------
lfs_val = run(
    "kubectl get deploy argocd-repo-server -n argocd "
    "-o jsonpath='{.spec.template.spec.containers[0].env"
    "[?(@.name==\"ARGOCD_GIT_LFS_ENABLED\")].value}'"
)

check_lfs = lfs_val == "true"


# ------------------------------------------------------------
# CHECK 5 — Service endpoints restored
# ------------------------------------------------------------
eps = run(
    f"kubectl get endpoints {DEPLOY} -n {NS} "
    "-o jsonpath='{.subsets}'"
)

check_eps = eps not in ("", "[]", "<no value>")


# ------------------------------------------------------------
# Final scoring
# ------------------------------------------------------------
checks = [
    check_binary,
    check_ready,
    check_uid,
    check_lfs,
    check_eps,
]

score = sum(checks) / len(checks)

result = {
    "score": score,
    "passed": sum(checks),
    "total": len(checks),
}

print(json.dumps(result))