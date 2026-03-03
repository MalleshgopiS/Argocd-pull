#!/bin/bash
set -e

kubectl create namespace bleater || true

mkdir -p /workspace/repo
cd /workspace/repo

git init
git lfs install

git lfs track "*.wasm"

# Create REAL WASM binary
printf '\x00\x61\x73\x6d\x01\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x10\x11\x12' > app.wasm

git add .gitattributes app.wasm
git commit -m "Add wasm"

# Save real SHA256 for grader
sha256sum app.wasm | awk '{print $1}' > /workspace/expected_sha

# Simulate broken deployment (only pointer file)
git show HEAD:app.wasm > /workspace/pointer_file
cp /workspace/pointer_file /workspace/repo/app.wasm

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
        - name: wasm
          mountPath: /usr/share/nginx/html
      volumes:
      - name: wasm
        hostPath:
          path: /workspace/repo
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