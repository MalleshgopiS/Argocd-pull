#!/usr/bin/env bash
set -e

NAMESPACE=bleater
DEPLOYMENT=bleater-frontend

kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Broken frontend deployment with LFS pointer file
kubectl apply -n $NAMESPACE -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $DEPLOYMENT
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
        image: busybox
        command: ["sh","-c"]
        args:
          - |
            mkdir -p /app;
            echo "version https://git-lfs.github.com/spec/v1" > /app/app.wasm;
            sleep 3600;
        readinessProbe:
          exec:
            command: ["cat","/app/app.wasm"]
          initialDelaySeconds: 3
          periodSeconds: 5
EOF

kubectl expose deployment $DEPLOYMENT \
  -n $NAMESPACE \
  --port=80 \
  --target-port=80 \
  --name=$DEPLOYMENT

# Save original UID
kubectl get deploy $DEPLOYMENT -n $NAMESPACE \
  -o jsonpath='{.metadata.uid}' > /tmp/frontend-deploy-uid

# Simulated ArgoCD repo-server without LFS enabled
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n argocd -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argocd-repo-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: repo-server
  template:
    metadata:
      labels:
        app: repo-server
    spec:
      containers:
      - name: repo-server
        image: busybox
        command: ["sleep","3600"]
EOF

echo "Broken LFS environment initialized."
sleep infinity