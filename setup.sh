#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# ArgoCD Git LFS Broken — Setup Script
#
# This setup intentionally creates a BROKEN state:
#
# 1. Frontend receives Git LFS POINTER instead of binary WASM
# 2. ArgoCD repo-server has Git LFS DISABLED
# 3. Deployment becomes unhealthy
#
# The grader later verifies:
#   - WASM no longer contains LFS pointer
#   - Deployment becomes Ready
#   - Deployment UID is preserved
#   - Repo-server has ARGOCD_GIT_LFS_ENABLED=true
#   - Service endpoints exist
#
# IMPORTANT:
# This script creates /grader/frontend-deploy-uid
# used by grader anti-cheating validation.
###############################################################################

echo "========================================"
echo "ArgoCD Git LFS Broken Task Setup"
echo "========================================"

############################################
# Namespace
############################################

echo "Creating namespace..."
kubectl create namespace bleater --dry-run=client -o yaml | kubectl apply -f -

############################################
# RBAC — allow ubuntu user to patch ArgoCD
############################################

echo "Granting ubuntu-user full access to argocd namespace..."

cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ubuntu-user-argocd-admin
  namespace: argocd
rules:
- apiGroups: ["", "apps", "argoproj.io"]
  resources: ["*"]
  verbs: ["*"]
EOF

cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ubuntu-user-argocd-admin-binding
  namespace: argocd
subjects:
- kind: ServiceAccount
  name: ubuntu-user
  namespace: default
roleRef:
  kind: Role
  name: ubuntu-user-argocd-admin
  apiGroup: rbac.authorization.k8s.io
EOF

############################################
# Broken WASM (Git LFS pointer file)
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
    oid sha256:deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef
    size 123456
EOF

############################################
# Broken Frontend Deployment
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
# Service
############################################

echo "Creating service..."

kubectl expose deployment bleater-frontend \
  -n bleater \
  --port=80 \
  --target-port=80 \
  --name=bleater-frontend \
  --dry-run=client -o yaml | kubectl apply -f -

############################################
# ArgoCD Application (required for refresh)
############################################

echo "Creating ArgoCD Application..."

cat <<EOF | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: bleater-frontend
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://example.com/fake-repo.git
    targetRevision: HEAD
    path: .
  destination:
    server: https://kubernetes.default.svc
    namespace: bleater
  syncPolicy:
    automated:
      prune: false
      selfHeal: true
EOF

############################################
# Save Deployment UID (ANTI-CHEAT)
############################################

echo "Saving Deployment UID for grader..."

DEPLOY_UID=$(kubectl get deployment bleater-frontend \
  -n bleater \
  -o jsonpath='{.metadata.uid}')

mkdir -p /grader
echo "$DEPLOY_UID" > /grader/frontend-deploy-uid

echo "UID saved to /grader/frontend-deploy-uid"

############################################
echo "Setup complete."
############################################