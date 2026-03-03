#!/bin/bash
set -e

ARGO_NS="argocd"
APP_NS="bleater"
SECRET_NAME="repo-bleater-frontend"
APP_NAME="bleater-frontend"

echo "[Solution] Enabling Git LFS in repository secret..."

kubectl patch secret ${SECRET_NAME} -n ${ARGO_NS} \
  --type merge \
  -p '{"stringData":{"enableLFS":"true"}}'

echo "[Solution] Verifying git-lfs exists..."

kubectl -n ${ARGO_NS} exec deploy/argocd-repo-server -- git lfs version >/dev/null

echo "[Solution] Restarting repo-server..."

kubectl -n ${ARGO_NS} rollout restart deployment argocd-repo-server
kubectl -n ${ARGO_NS} rollout status deployment argocd-repo-server

echo "[Solution] Forcing ArgoCD application refresh..."

kubectl -n ${ARGO_NS} patch application ${APP_NAME} \
  --type merge \
  -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'

echo "[Solution Completed]"