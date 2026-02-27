#!/usr/bin/env bash
set -euo pipefail

NS="bleater"
DEPLOY="bleater-frontend"

echo "Creating namespace..."
kubectl create namespace $NS --dry-run=client -o yaml | kubectl apply -f -

echo "Deploying broken frontend..."

kubectl apply -n $NS -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $DEPLOY
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
        image: nginx:alpine
        command: ["/bin/sh","-c"]
        args:
          - |
            mkdir -p /app
            # simulate Git LFS pointer instead of binary
            cat <<LFS > /app/app.wasm
version https://git-lfs.github.com/spec/v1
oid sha256:deadbeef
size 12345
LFS
            nginx -g 'daemon off;'
        volumeMounts:
        - name: app
          mountPath: /app
      volumes:
      - name: app
        emptyDir: {}
EOF

kubectl expose deployment $DEPLOY -n $NS --port 80 --target-port 80 || true

echo "Waiting for deployment..."
kubectl rollout status deployment/$DEPLOY -n $NS --timeout=120s

echo "Saving Deployment UID..."

mkdir -p /grader

DEPLOY_UID=$(kubectl get deploy $DEPLOY -n $NS -o jsonpath='{.metadata.uid}')

echo "$DEPLOY_UID" > /grader/frontend-deploy-uid

echo "Setup complete."