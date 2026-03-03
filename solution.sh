#!/bin/bash
set -e

ARGO_NS="argocd"
APP_NAME="bleater-platform"
SECRET_NAME="repo-bleater-platform"

echo "[Solution] Enabling Git LFS..."

kubectl -n ${ARGO_NS} patch secret ${SECRET_NAME} \
  --type merge \
  -p '{"stringData":{"enableLFS":"true"}}'

echo "[Solution] Restarting repo-server..."

kubectl -n ${ARGO_NS} rollout restart deployment argocd-repo-server
kubectl -n ${ARGO_NS} rollout status deployment argocd-repo-server

echo "[Solution] Forcing ArgoCD refresh..."

kubectl -n ${ARGO_NS} annotate application ${APP_NAME} \
  argocd.argoproj.io/refresh=hard --overwrite

echo "[Solution Complete]"