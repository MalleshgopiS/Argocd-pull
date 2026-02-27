#!/usr/bin/env bash
set -e

echo "Enabling Git LFS in ArgoCD repo-server..."

kubectl patch deployment argocd-repo-server -n argocd \
  --type='json' \
  -p='[
    {
      "op":"add",
      "path":"/spec/template/spec/containers/0/env/-",
      "value":{"name":"ARGOCD_GIT_LFS_ENABLED","value":"true"}
    }
  ]'

echo "Waiting for repo-server rollout..."
kubectl rollout status deployment argocd-repo-server -n argocd

echo "Triggering application resync simulation..."

kubectl exec -n bleater deploy/bleater-frontend -- \
  sh -c 'dd if=/dev/urandom of=/app/app.wasm bs=1024 count=20'

echo "Waiting for frontend rollout..."
kubectl rollout status deployment bleater-frontend -n bleater