#!/usr/bin/env bash
set -euo pipefail

echo "========================================"
echo "ArgoCD Git LFS Broken Task Setup"
echo "========================================"

NS="bleater"

echo "Creating namespace..."
kubectl create namespace ${NS} || true

echo "Grant ubuntu-user access to argocd..."
kubectl create role ubuntu-user-argocd-admin \
  --verb="*" \
  --resource="*" \
  -n argocd || true

kubectl create rolebinding ubuntu-user-argocd-admin-binding \
  --role=ubuntu-user-argocd-admin \
  --user=ubuntu-user \
  -n argocd || true


echo "Creating broken WASM ConfigMap..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: wasm-config
  namespace: ${NS}
data:
  app.wasm: |
    version https://git-lfs.github.com/spec/v1
    oid sha256:broken
    size 123
EOF


echo "Deploying broken frontend..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bleater-frontend
  namespace: ${NS}
  labels:
    app: frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: harbor.devops.local/library/nginx:1.25
          imagePullPolicy: IfNotPresent
          command: ["/bin/sh","-c"]
          args:
            - |
              mkdir -p /app;
              mkdir -p /usr/share/nginx/html;
              cp /wasm/app.wasm /app/app.wasm;
              cp /wasm/app.wasm /usr/share/nginx/html/app.wasm;
              nginx -g 'daemon off;';
          volumeMounts:
            - name: wasm
              mountPath: /wasm
      volumes:
        - name: wasm
          configMap:
            name: wasm-config
EOF


echo "Creating service..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: bleater-frontend
  namespace: ${NS}
spec:
  selector:
    app: frontend
  ports:
    - port: 80
      targetPort: 80
EOF


echo "Saving Deployment UID for grader..."
kubectl get deployment bleater-frontend \
  -n ${NS} \
  -o jsonpath='{.metadata.uid}' > /grader/frontend-deploy-uid

echo "Setup complete."