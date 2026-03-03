#!/bin/bash
supervisord -c /etc/supervisor/supervisord.conf &
until kubectl get pods -n kube-system &> /dev/null; do sleep 2; done

# Setup the broken repository state
mkdir -p /data/repo
cd /data/repo && git init
echo "pointer-data-not-binary" > app.wasm
git add app.wasm && git commit -m "Initial commit"

# Trust the local repo
argocd repo add file:///data/repo --insecure

# Deploy the ArgoCD application
kubectl apply -f /data/argo-app.yaml
argocd app sync bleater-ui --force