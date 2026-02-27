#!/usr/bin/env bash
set -euo pipefail

ARGO_NS="argocd"
APP_NS="bleater"
APP_NAME="bleater-frontend"

echo "Enabling Git LFS in ArgoCD repo-server..."

# Idempotent env injection (avoids duplicate env var failures)
kubectl set env deployment/argocd-repo-server \
  -n ${ARGO_NS} \
  ARGOCD_GIT_LFS_ENABLED=true

echo "Waiting for repo-server rollout..."
kubectl rollout status deployment/argocd-repo-server \
  -n ${ARGO_NS} \
  --timeout=300s


echo "Triggering ArgoCD refresh..."
kubectl annotate application ${APP_NAME} \
  -n ${ARGO_NS} \
  argocd.argoproj.io/refresh=hard \
  --overwrite || true


# ---- FIX: wait for ArgoCD controller to actually reconcile ----
echo "Waiting for ArgoCD sync..."

until [[ "$(kubectl get application ${APP_NAME} -n ${ARGO_NS} \
  -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "")" == "Synced" ]]; do
  sleep 5
done

echo "Waiting for ArgoCD health..."

until [[ "$(kubectl get application ${APP_NAME} -n ${ARGO_NS} \
  -o jsonpath='{.status.health.status}' 2>/dev/null || echo "")" == "Healthy" ]]; do
  sleep 5
done


echo "Waiting for frontend recovery..."
kubectl rollout status deployment/${APP_NAME} \
  -n ${APP_NS} \
  --timeout=300s

echo "Fix complete."