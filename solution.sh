#!/usr/bin/env bash
set -euo pipefail

ARGO_NS="argocd"
APP_NS="bleater"
APP_NAME="bleater-frontend"

echo "Enabling Git LFS in ArgoCD repo-server..."

# Idempotent env injection (safe if already set)
kubectl set env deployment/argocd-repo-server \
  -n ${ARGO_NS} \
  ARGOCD_GIT_LFS_ENABLED=true || true

echo "Waiting for repo-server rollout..."
kubectl rollout status deployment/argocd-repo-server \
  -n ${ARGO_NS} \
  --timeout=300s

echo "Triggering ArgoCD refresh..."
kubectl annotate application ${APP_NAME} \
  -n ${ARGO_NS} \
  argocd.argoproj.io/refresh=hard \
  --overwrite || true


# ---- Optimized Convergence Wait ----

echo "Waiting for frontend deployment rollout..."

kubectl rollout status deployment/${APP_NAME} \
  -n ${APP_NS} \
  --timeout=300s


echo "Verifying pods are Ready..."

kubectl wait \
  --for=condition=Ready pods \
  -l app=${APP_NAME} \
  -n ${APP_NS} \
  --timeout=180s


echo "Fix complete."