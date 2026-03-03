#!/bin/bash
set -e

ARGO_NS="argocd"
APP_NS="bleater"
SECRET_NAME="repo-bleater-frontend"

echo "[Setup] Recording original Deployment UID..."
kubectl -n ${APP_NS} get deployment bleater-frontend \
  -o jsonpath='{.metadata.uid}' > /tmp/original_uid

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