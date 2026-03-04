#!/bin/bash
set -euo pipefail

echo "=========================================="
echo "Starting setup for git-lfs-wasm-fix task"
echo "=========================================="

############################################
# 1️⃣ Wait for Kubernetes to be ready
############################################

echo "Waiting for Kubernetes API to become ready..."

for i in {1..60}; do
    if kubectl get nodes >/dev/null 2>&1; then
        echo "Kubernetes is ready."
        break
    fi
    sleep 2
done

if ! kubectl get nodes >/dev/null 2>&1; then
    echo "ERROR: Kubernetes did not become ready in time."
    exit 1
fi

############################################
# 2️⃣ Create namespace
############################################

kubectl create namespace bleater 2>/dev/null || true

############################################
# 3️⃣ Initialize Git LFS repository
############################################

mkdir -p /workspace/repo
cd /workspace/repo

git init
git config user.email "nebula@example.com"
git config user.name "Nebula"

git lfs install --local

# Track wasm files with LFS
git lfs track "*.wasm"

############################################
# 4️⃣ Create REAL WASM binary
############################################

# Minimal but deterministic wasm-like binary
printf '\x00\x61\x73\x6dREALCONTENT1234567890' > app.wasm

git add .gitattributes app.wasm
git commit -m "Add real wasm file"

############################################
# 5️⃣ Store expected SHA securely
############################################

REAL_SHA=$(sha256sum app.wasm | awk '{print $1}')
echo "$REAL_SHA" > /tmp/internal_expected_sha
chmod 600 /tmp/internal_expected_sha

############################################
# 6️⃣ Replace working tree with LFS pointer
############################################

# Overwrite working copy with pointer file
git lfs pointer --file=app.wasm > app.wasm

echo "Pointer file deployed instead of real binary."

############################################
# 7️⃣ Deploy Kubernetes workload
############################################

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bleater-frontend
  namespace: bleater
spec:
  replicas: 1
  selector:
    matchLabels:
      app: bleater-frontend
  template:
    metadata:
      labels:
        app: bleater-frontend
    spec:
      containers:
      - name: frontend
        image: nginx:alpine
        volumeMounts:
        - name: repo
          mountPath: /usr/share/nginx/html
      volumes:
      - name: repo
        hostPath:
          path: /workspace/repo
          type: Directory
---
apiVersion: v1
kind: Service
metadata:
  name: bleater-frontend
  namespace: bleater
spec:
  selector:
    app: bleater-frontend
  ports:
  - port: 80
    targetPort: 80
EOF

############################################
# 8️⃣ Wait for deployment to become ready
############################################

echo "Waiting for deployment to become ready..."

for i in {1..60}; do
    READY=$(kubectl get deploy bleater-frontend -n bleater -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    if [[ "$READY" == "1" ]]; then
        echo "Deployment is ready."
        break
    fi
    sleep 2
done

if [[ "$READY" != "1" ]]; then
    echo "ERROR: Deployment did not become ready."
    exit 1
fi

############################################
# 9️⃣ Final confirmation
############################################

echo "=========================================="
echo "Setup complete. Broken LFS state created."
echo "=========================================="