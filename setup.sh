#!/bin/bash
set -e

NAMESPACE="argocd"
REPO_SECRET="repo-bleater-frontend"

echo "[Setup] Creating repository secret WITHOUT Git LFS enabled..."

kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: ${REPO_SECRET}
  namespace: ${NAMESPACE}
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  url: https://github.com/your-org/bleater-frontend.git
  type: git
EOF

echo "[Setup] Restarting repo-server to ensure broken state..."

kubectl -n ${NAMESPACE} rollout restart deployment argocd-repo-server
kubectl -n ${NAMESPACE} rollout status deployment argocd-repo-server

echo "[Setup Complete]"
echo "Frontend will crash because Git LFS objects are not fetched."