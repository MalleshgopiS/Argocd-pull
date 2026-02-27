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

kubectl rollout status deployment argocd-repo-server -n argocd

echo "Triggering reconciliation..."
kubectl rollout restart deployment bleater-frontend -n bleater
kubectl rollout status deployment bleater-frontend -n bleater

echo "Fix applied."