#!/bin/bash
set -e

# ------------------------------------------------------------
# ArgoCD LFS Broken Task Setup
#
# This script:
# 1. Deploys frontend workload
# 2. Ensures repo-server lacks Git LFS support
# 3. Injects WASM LFS pointer content
# 4. Stores Deployment UID for anti-cheating validation
# ------------------------------------------------------------

NS="bleater"

kubectl create namespace $NS --dry-run=client -o yaml | kubectl apply -f -

# Fake broken deployment (contains LFS pointer)
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bleater-frontend
  namespace: $NS
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: nginx
        command: ["/bin/sh","-c"]
        args:
          - |
            mkdir -p /app;
            echo "version https://git-lfs.github.com/spec/v1" > /app/app.wasm;
            nginx -g 'daemon off;';
EOF

kubectl expose deployment bleater-frontend \
  --port=80 --target-port=80 \
  -n $NS --name bleater-frontend || true

echo "Saving Deployment UID..."

UID=$(kubectl get deploy bleater-frontend -n $NS -o jsonpath='{.metadata.uid}')

mkdir -p /grader
echo "$UID" > /grader/frontend-deploy-uid
chmod 400 /grader/frontend-deploy-uid

echo "Setup complete."