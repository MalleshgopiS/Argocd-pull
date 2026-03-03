import subprocess
import time
import json
import sys
import signal
import os

MAX_SCORE = 1.0

def run(cmd):
    return subprocess.check_output(cmd, shell=True).decode().strip()

def wait_for_deployment(timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        try:
            ready = run("kubectl get deploy bleater-frontend -n bleater -o jsonpath='{.status.readyReplicas}'")
            replicas = run("kubectl get deploy bleater-frontend -n bleater -o jsonpath='{.status.replicas}'")
            if ready == replicas and ready not in ["", "0", "None"]:
                return True
        except:
            pass
        time.sleep(2)
    return False

def check_wasm_magic():
    try:
        output = run(
            "kubectl exec -n bleater deploy/bleater-frontend -- "
            "head -c 4 /usr/share/nginx/html/static/app.wasm | xxd -p"
        )
        return output.startswith("0061736d")
    except:
        return False

def check_wasm_size():
    try:
        size = run(
            "kubectl exec -n bleater deploy/bleater-frontend -- "
            "stat -c%s /usr/share/nginx/html/static/app.wasm"
        )
        return int(size) > 8
    except:
        return False

def check_pointer_removed():
    try:
        content = run(
            "kubectl exec -n bleater deploy/bleater-frontend -- "
            "grep -c 'git-lfs.github.com' /usr/share/nginx/html/static/app.wasm || true"
        )
        return content == "0"
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
    score = 0.0
    details = {}

    if wait_for_deployment():
        score += 0.2
        details["deployment_ready"] = True
    else:
        details["deployment_ready"] = False

    if check_wasm_magic():
        score += 0.3
        details["wasm_magic_valid"] = True
    else:
        details["wasm_magic_valid"] = False

    if check_wasm_size():
        score += 0.2
        details["wasm_size_valid"] = True
    else:
        details["wasm_size_valid"] = False

    if check_pointer_removed():
        score += 0.2
        details["pointer_removed"] = True
    else:
        details["pointer_removed"] = False

    if check_http():
        score += 0.1
        details["http_ok"] = True
    else:
        details["http_ok"] = False

    return round(score, 2), details


if __name__ == "__main__":
    score, details = grade()

    result = {
        "score": score,
        "max_score": MAX_SCORE,
        "details": details
    }

    print(json.dumps(result))

    if score == 0:
        sys.exit(1)
    else:
        sys.exit(0)