#!/bin/bash
set -e

kubectl create namespace bleater || true

mkdir -p /workspace/repo/static

# Broken LFS pointer file
cat <<EOF > /workspace/repo/static/app.wasm
version https://git-lfs.github.com/spec/v1
oid sha256:deadbeef123456789
size 123456
EOF

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
        - name: static
          mountPath: /usr/share/nginx/html/static
      volumes:
      - name: static
        hostPath:
          path: /workspace/repo/static
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