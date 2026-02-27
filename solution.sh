#!/usr/bin/env bash
set -e

NS=argocd
APP_NS=bleater

echo "Enabling Git LFS in ArgoCD repo-server..."

kubectl patch deployment argocd-repo-server -n $NS \
  --type='json' \
  -p='[
    {
      "op":"add",
      "path":"/spec/template/spec/containers/0/env/-",
      "value":{"name":"ARGOCD_GIT_LFS_ENABLED","value":"true"}
    }
  ]'

echo "Waiting for repo-server restart..."
kubectl rollout status deployment argocd-repo-server -n $NS

echo "Triggering GitOps reconciliation (simulated ArgoCD sync)..."

# restart workload so repo-server pulls repo again
kubectl rollout restart deployment bleater-frontend -n $APP_NS

kubectl rollout status deployment bleater-frontend -n $APP_NS

echo "LFS fix applied successfully."