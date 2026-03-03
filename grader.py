import subprocess
import time
import hashlib
import json
import sys

MAX_SCORE = 1.0

def run(cmd):
    return subprocess.check_output(cmd, shell=True).decode().strip()

def wait_for_ready(timeout=120):
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

def check_sha():
    try:
        expected = open("/workspace/expected_sha").read().strip()

        actual = run(
            "kubectl exec -n bleater deploy/bleater-frontend -- "
            "sha256sum /usr/share/nginx/html/app.wasm | awk '{print $1}'"
        )

        return actual == expected
    except:
        return False

def check_http():
    try:
        pf = subprocess.Popen(
            "kubectl port-forward svc/bleater-frontend 8080:80 -n bleater",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(3)
        code = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/")
        pf.terminate()
        return code == "200"
    except:
        return False

def grade():
    score = 0
    details = {}

    if wait_for_ready():
        score += 0.4
        details["deployment_ready"] = True
    else:
        details["deployment_ready"] = False

    if check_sha():
        score += 0.4
        details["correct_lfs_object"] = True
    else:
        details["correct_lfs_object"] = False

    if check_http():
        score += 0.2
        details["http_ok"] = True
    else:
        details["http_ok"] = False

    return round(score,2), details

if __name__ == "__main__":
    score, details = grade()

    result = {
        "score": score,
        "max_score": MAX_SCORE,
        "details": details
    }

    print(json.dumps(result))

    sys.exit(0 if score > 0 else 1)