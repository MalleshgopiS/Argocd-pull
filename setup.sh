#!/bin/bash
set -e

ARGO_NS="argocd"
APP_NS="bleater"
SECRET_NAME="repo-bleater-frontend"

echo "[Setup] Discovering frontend deployment dynamically..."

# Find deployment created by ArgoCD in bleater namespace
DEPLOYMENT_NAME=$(kubectl -n ${APP_NS} get deployments \
  -o jsonpath='{.items[?(@.metadata.labels.app\.kubernetes\.io/instance=="bleater-frontend")].metadata.name}')

if [ -z "$DEPLOYMENT_NAME" ]; then
  echo "ERROR: Could not find frontend deployment"
  exit 1
fi

echo "[Setup] Found deployment: $DEPLOYMENT_NAME"

kubectl -n ${APP_NS} get deployment ${DEPLOYMENT_NAME} \
  -o jsonpath='{.metadata.uid}' > /var/tmp/original_uid

echo "[Setup] Creating repository secret WITHOUT LFS enabled..."

kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: ${SECRET_NAME}
  namespace: ${ARGO_NS}
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  url: https://github.com/your-org/bleater-frontend.git
  type: git
EOF

kubectl -n ${ARGO_NS} rollout restart deployment argocd-repo-server
kubectl -n ${ARGO_NS} rollout status deployment argocd-repo-server

echo "[Setup Complete]"