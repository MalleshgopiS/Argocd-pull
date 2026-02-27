#!/usr/bin/env bash
set -e

kubectl create namespace bleater || true
kubectl create namespace argocd || true

# -------------------------------------------------
# Create broken frontend deployment
# -------------------------------------------------
cat <<EOF | kubectl apply -n bleater -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bleater-frontend
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
        command: ["/bin/sh"]
        args:
          - -c
          - |
            mkdir -p /app
            echo "version https://git-lfs.github.com/spec/v1" > /app/app.wasm
            nginx -g 'daemon off;'
        ports:
        - containerPort: 80
EOF

# -------------------------------------------------
# Service
# -------------------------------------------------
kubectl expose deployment bleater-frontend \
  --port=80 \
  --target-port=80 \
  -n bleater \
  --name=bleater-frontend || true

# -------------------------------------------------
# Fake argocd repo-server
# -------------------------------------------------
cat <<EOF | kubectl apply -n argocd -f -
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
        image: nginx
        env: []
EOF

# -------------------------------------------------
# Save original UID in protected grader location
# -------------------------------------------------
kubectl get deploy bleater-frontend -n bleater \
  -o jsonpath='{.metadata.uid}' > /grader/frontend-deploy-uid

chmod 400 /grader/frontend-deploy-uid