#!/bin/bash
set -e

ARGO_NS="argocd"
APP_NS="bleater"
APP_NAME="bleater-platform"
SECRET_NAME="repo-bleater-platform"

echo "[Setup] Extracting repository URL from ArgoCD Application..."

REPO_URL=$(kubectl -n ${ARGO_NS} get application ${APP_NAME} \
  -o jsonpath='{.spec.source.repoURL}')

if [ -z "$REPO_URL" ]; then
  echo "ERROR: Could not extract repoURL from ArgoCD Application"
  exit 1
fi

echo "[Setup] Repo URL: $REPO_URL"

echo "[Setup] Locating frontend deployment by WASM presence..."

DEPLOYMENT_NAME=""

for d in $(kubectl -n ${APP_NS} get deployments -o jsonpath='{.items[*].metadata.name}'); do
    POD=$(kubectl -n ${APP_NS} get pods \
        --selector=app=${d} \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

    if [ -n "$POD" ]; then
        if kubectl -n ${APP_NS} exec $POD -- test -f /app/app.wasm 2>/dev/null; then
            DEPLOYMENT_NAME=$d
            break
        fi
    fi
done

if [ -z "$DEPLOYMENT_NAME" ]; then
    echo "ERROR: Could not locate frontend deployment"
    exit 1
fi

echo "[Setup] Found frontend deployment: $DEPLOYMENT_NAME"

# Save original Deployment UID
kubectl -n ${APP_NS} get deployment ${DEPLOYMENT_NAME} \
  -o jsonpath='{.metadata.uid}' > /var/tmp/original_uid

# Save original repo-server resourceVersion
kubectl -n ${ARGO_NS} get deployment argocd-repo-server \
  -o jsonpath='{.metadata.resourceVersion}' > /var/tmp/repo_server_rv

echo "[Setup] Creating repository secret WITHOUT enableLFS..."

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
  url: ${REPO_URL}
  type: git
EOF

kubectl -n ${ARGO_NS} rollout restart deployment argocd-repo-server
kubectl -n ${ARGO_NS} rollout status deployment argocd-repo-server

echo "[Setup Complete]"