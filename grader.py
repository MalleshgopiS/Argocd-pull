import subprocess
import time
import hashlib
import json
import sys
import os

MAX_SCORE = 1.0

# Internal expected SHA (not accessible to agent)
EXPECTED_SHA = None

def load_expected_sha():
    """
    Loads the expected SHA256 hash of the real WASM file.
    This value is generated during setup and stored in a
    protected temporary location not accessible to the agent.
    """
    global EXPECTED_SHA
    with open("/tmp/internal_expected_sha", "r") as f:
        EXPECTED_SHA = f.read().strip()


def run(cmd):
    return subprocess.check_output(cmd, shell=True).decode().strip()


def wait_for_ready(timeout=120):
    """
    Wait until the Kubernetes deployment reports 1 ready replica.
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            ready = run("kubectl get deploy bleater-frontend -n bleater -o jsonpath='{.status.readyReplicas}'")
            if ready == "1":
                return True
        except:
            pass
        time.sleep(2)
    return False


def check_sha_match():
    """
    Verifies that the deployed app.wasm file SHA256 matches
    the original Git LFS object.
    """
    try:
        actual = run(
            "kubectl exec -n bleater deploy/bleater-frontend -- "
            "sha256sum /usr/share/nginx/html/app.wasm | awk '{print $1}'"
        )
        return actual == EXPECTED_SHA
    except:
        return False


def check_http():
    """
    Ensures the HTTP endpoint responds with status 200.
    """
    try:
        pf = subprocess.Popen(
            "kubectl port-forward svc/bleater-frontend 18080:80 -n bleater",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Wait until port is open instead of fixed sleep
        for _ in range(10):
            try:
                code = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:18080/")
                pf.terminate()
                return code == "200"
            except:
                time.sleep(1)

        pf.terminate()
        return False
    except:
        return False


def grade():
    """
    Runs all grading checks and returns total score and details.
    """
    score = 0.0
    details = {}

    if wait_for_ready():
        score += 0.4
        details["deployment_ready"] = True
    else:
        details["deployment_ready"] = False

    if check_sha_match():
        score += 0.4
        details["lfs_object_correct"] = True
    else:
        details["lfs_object_correct"] = False

    if check_http():
        score += 0.2
        details["http_ok"] = True
    else:
        details["http_ok"] = False

    return round(score, 2), details


if __name__ == "__main__":
    load_expected_sha()
    score, details = grade()

    result = {
        "score": score,
        "max_score": MAX_SCORE,
        "details": details
    }

    print(json.dumps(result))
    sys.exit(0 if score > 0 else 1)