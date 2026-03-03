#!/bin/bash
set -e

NAMESPACE="argocd"
REPO_SECRET="repo-bleater-frontend"

echo "[Solution] Enabling Git LFS for repository..."

<<<<<<< HEAD
kubectl patch secret ${REPO_SECRET} -n ${NAMESPACE} \
  --type merge \
  -p '{"stringData":{"enableLFS":"true"}}'

echo "[Solution] Verifying git-lfs is available in repo-server..."
=======
kubectl set env deployment/argocd-repo-server \
  -n ${ARGO_NS} \
  ARGOCD_GIT_LFS_ENABLED=true


echo "Waiting for repo-server rollout..."
kubectl rollout status deployment/argocd-repo-server \
  -n ${ARGO_NS} \
  --timeout=300s
>>>>>>> 3255ed050bac464c09bb67a26b7c8a846bfd756c

if ! kubectl -n ${NAMESPACE} exec deploy/argocd-repo-server -- git lfs version >/dev/null 2>&1; then
  echo "ERROR: git-lfs is not installed in repo-server container"
  exit 1
fi

echo "[Solution] Restarting repo-server..."

kubectl -n ${NAMESPACE} rollout restart deployment argocd-repo-server
kubectl -n ${NAMESPACE} rollout status deployment argocd-repo-server

<<<<<<< HEAD
echo "[Solution Complete]"
=======
echo "Waiting for ArgoCD sync..."
until [[ "$(kubectl get application ${APP_NAME} -n ${ARGO_NS} \
  -o jsonpath='{.status.sync.status}' 2>/dev/null)" == "Synced" ]]; do
  sleep 5
done


echo "Waiting for ArgoCD health..."
until [[ "$(kubectl get application ${APP_NAME} -n ${ARGO_NS} \
  -o jsonpath='{.status.health.status}' 2>/dev/null)" == "Healthy" ]]; do
  sleep 5
done


echo "Waiting for frontend rollout..."
kubectl rollout status deployment/${APP_NAME} \
  -n ${APP_NS} \
  --timeout=300s

echo "Fix complete."
>>>>>>> 3255ed050bac464c09bb67a26b7c8a846bfd756c
