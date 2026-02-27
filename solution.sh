#!/usr/bin/env bash
set -e

NS=bleater

echo "Enabling Git LFS in ArgoCD repo-server..."

kubectl patch deployment argocd-repo-server -n argocd \
  --type='json' \
  -p='[
    {
      "op":"add",
      "path":"/spec/template/spec/containers/0/env",
      "value":[{"name":"ARGOCD_GIT_LFS_ENABLED","value":"true"}]
    }
  ]'

echo "Replacing LFS pointer file with binary..."

kubectl exec -n $NS deploy/bleater-frontend -- \
  sh -c 'echo "REAL_BINARY_CONTENT" > /app/app.wasm'

kubectl rollout status deployment bleater-frontend -n $NS