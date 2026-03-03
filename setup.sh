#!/bin/bash
set -e

kubectl create namespace bleater || true

mkdir -p /workspace/repo
cd /workspace/repo

git init
git lfs install
git lfs track "*.wasm"

# Create real WASM binary
printf '\x00\x61\x73\x6d\x01\x00\x00\x00REALWASMCONTENT1234567890' > app.wasm

git add .gitattributes app.wasm
git commit -m "Add real wasm"

# Save SHA internally (not exposed to agent later)
REAL_SHA=$(sha256sum app.wasm | awk '{print $1}')
echo $REAL_SHA > /tmp/internal_expected_sha

# Replace working tree with pointer version
git show HEAD:app.wasm > pointer.tmp
mv pointer.tmp app.wasm

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