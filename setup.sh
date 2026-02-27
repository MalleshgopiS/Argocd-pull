#!/usr/bin/env bash
set -euo pipefail

echo "========================================"
echo "ArgoCD Git LFS Broken Task Setup"
echo "========================================"

############################################
# Create Namespace
############################################

echo "Creating namespace..."

kubectl create namespace bleater --dry-run=client -o yaml | kubectl apply -f -

############################################
# Grant ubuntu-user access to argocd namespace
# (FIX: required so solution.sh can patch repo-server)
############################################

echo "Granting ubuntu-user RBAC access to argocd namespace..."

kubectl create role ubuntu-user-argocd-admin \
  --namespace argocd \
  --verb='*' \
  --resource='*' \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create rolebinding ubuntu-user-argocd-admin-binding \
  --namespace argocd \
  --role=ubuntu-user-argocd-admin \
  --serviceaccount=default:ubuntu-user \
  --dry-run=client -o yaml | kubectl apply -f -

############################################
# Create broken WASM config (Git LFS pointer)
############################################

echo "Creating broken WASM ConfigMap..."

cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: wasm-config
  namespace: bleater
data:
  app.wasm: |
    version https://git-lfs.github.com/spec/v1
    oid sha256:deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef
    size 123456
EOF

############################################
# Deploy Broken Frontend
############################################

echo "Deploying broken frontend..."

cat <<'EOF' | kubectl apply -f -
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
          image: nginx:1.25
          command: ["/bin/sh","-c"]
          args:
            - |
              mkdir -p /usr/share/nginx/html;
              cp /wasm/app.wasm /usr/share/nginx/html/app.wasm;
              nginx -g 'daemon off;';
          volumeMounts:
            - name: wasm
              mountPath: /wasm
      volumes:
        - name: wasm
          configMap:
            name: wasm-config
EOF

############################################
# Create Service
############################################

echo "Creating service..."

kubectl expose deployment bleater-frontend \
  -n bleater \
  --port=80 \
  --target-port=80 \
  --name=bleater-frontend \
  --dry-run=client -o yaml | kubectl apply -f -

############################################
# Save Deployment UID (ANTI-CHEAT CHECK)
############################################

echo "Saving Deployment UID..."

DEPLOY_UID=$(kubectl get deployment bleater-frontend \
  -n bleater \
  -o jsonpath='{.metadata.uid}')

mkdir -p /grader
echo "$DEPLOY_UID" > /grader/frontend-deploy-uid

############################################
# Done
############################################

echo "Setup complete."