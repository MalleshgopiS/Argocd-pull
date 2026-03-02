echo "Waiting for ArgoCD sync..."

SYNC_TIMEOUT=300
SYNC_START=$(date +%s)

while true; do
  STATUS=$(kubectl get application ${APP_NAME} -n ${ARGO_NS} \
    -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "")

  if [[ "$STATUS" == "Synced" ]]; then
    echo "Application synced."
    break
  fi

  NOW=$(date +%s)
  if (( NOW - SYNC_START > SYNC_TIMEOUT )); then
    echo "ERROR: ArgoCD sync timeout"
    exit 1
  fi

  sleep 3
done


echo "Waiting for ArgoCD health..."

HEALTH_TIMEOUT=300
HEALTH_START=$(date +%s)

while true; do
  HEALTH=$(kubectl get application ${APP_NAME} -n ${ARGO_NS} \
    -o jsonpath='{.status.health.status}' 2>/dev/null || echo "")

  if [[ "$HEALTH" == "Healthy" ]]; then
    echo "Application healthy."
    break
  fi

  NOW=$(date +%s)
  if (( NOW - HEALTH_START > HEALTH_TIMEOUT )); then
    echo "ERROR: ArgoCD health timeout"
    exit 1
  fi

  sleep 3
done