import subprocess
import time

NS="bleater"
DEPLOY="bleater-frontend"
UID_FILE="/tmp/frontend-deploy-uid"

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except:
        return ""

def wait_ready():
    for _ in range(10):
        r = run(f"kubectl get deploy {DEPLOY} -n {NS} -o jsonpath='{{.status.readyReplicas}}'")
        if r and r != "0":
            return True
        time.sleep(3)
    return False

def get_pod():
    return run(f"kubectl get pod -n {NS} -l app=frontend -o jsonpath='{{.items[0].metadata.name}}'")

# 1 WASM not pointer
pod = get_pod()
wasm_content = run(f"kubectl exec -n {NS} {pod} -- cat /app/app.wasm") if pod else ""
check1 = "git-lfs.github.com" not in wasm_content

# 2 Ready
check2 = wait_ready()

# 3 UID preserved
orig = run(f"cat {UID_FILE}")
curr = run(f"kubectl get deploy {DEPLOY} -n {NS} -o jsonpath='{{.metadata.uid}}'")
check3 = orig == curr

# 4 LFS enabled
envs = run("kubectl get deploy argocd-repo-server -n argocd -o jsonpath='{.spec.template.spec.containers[0].env}'")
check4 = "ARGOCD_GIT_LFS_ENABLED" in envs

# 5 Service endpoints
eps = run(f"kubectl get endpoints {DEPLOY} -n {NS} -o jsonpath='{{.subsets}}'")
check5 = eps != ""

checks = [check1,check2,check3,check4,check5]
score = sum(checks)/len(checks)

print({"score":score,"passed":sum(checks),"total":len(checks)})