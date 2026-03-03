import requests
import sys
import time

def check_wasm_integrity(retries=10):
    for i in range(retries):
        try:
            resp = requests.get("http://bleater-ui/app.wasm", timeout=5)
            # Magic number for WASM binary is \0asm
            if resp.content.startswith(b'\x00\x61\x73\x6d'):
                return True
        except:
            time.sleep(5)
    return False

def grade():
    subscores = {}
    subscores["gitattributes_configured"] = 1.0 if os.path.exists("/data/repo/.gitattributes") else 0.0
    subscores["wasm_binary_valid"] = 1.0 if check_wasm_integrity() else 0.0
    
    weights = {"gitattributes_configured": 0.5, "wasm_binary_valid": 0.5}
    return sum(subscores[k] * weights[k] for k in subscores)

if __name__ == "__main__":
    score = grade()
    sys.exit(0 if score >= 1.0 else 1)