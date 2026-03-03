#!/bin/bash
set -e

NAMESPACE="argocd"
REPO_SECRET="repo-bleater-frontend"

echo "[Solution] Enabling Git LFS for repository..."

kubectl patch secret ${REPO_SECRET} -n ${NAMESPACE} \
  --type merge \
  -p '{"stringData":{"enableLFS":"true"}}'

echo "[Solution] Verifying git-lfs is available in repo-server..."

if ! kubectl -n ${NAMESPACE} exec deploy/argocd-repo-server -- git lfs version >/dev/null 2>&1; then
  echo "ERROR: git-lfs is not installed in repo-server container"
  exit 1
fi

echo "[Solution] Restarting repo-server..."

kubectl -n ${NAMESPACE} rollout restart deployment argocd-repo-server
kubectl -n ${NAMESPACE} rollout status deployment argocd-repo-server

echo "[Solution Complete]"