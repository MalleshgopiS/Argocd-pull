#!/bin/bash
set -e

APP_NS="bleater"
ARGO_NS="argocd"

echo "Enabling Git LFS in ArgoCD repo-server..."

kubectl patch deployment argocd-repo-server \
  -n $ARGO_NS \
  --type='json' \
  -p='[
    {
      "op":"add",
      "path":"/spec/template/spec/containers/0/env/-",
      "value":{"name":"ARGOCD_GIT_LFS_ENABLED","value":"true"}
    }
  ]'

echo "Waiting for repo-server rollout..."
kubectl rollout status deployment argocd-repo-server -n $ARGO_NS

echo "Triggering ArgoCD refresh..."

kubectl annotate application bleater-frontend \
  -n $ARGO_NS \
  argocd.argoproj.io/refresh=hard --overwrite || true

echo "Waiting for frontend recovery..."
kubectl rollout status deployment bleater-frontend -n $APP_NS

echo "Fix complete."