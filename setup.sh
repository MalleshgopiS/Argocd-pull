#!/bin/bash
set -e

NS="bleater"
DEPLOY="bleater-frontend"

echo "Creating namespace..."
kubectl create namespace $NS --dry-run=client -o yaml | kubectl apply -f -

echo "Deploying broken frontend..."

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${DEPLOY}
  namespace: ${NS}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: bleater-frontend
  template:
    metadata:
      labels:
        app: bleater-frontend
    spec:
      containers:
        - name: frontend
          image: nginx:1.25
          ports:
            - containerPort: 80
          volumeMounts:
            - name: wasm
              mountPath: /usr/share/nginx/html
      volumes:
        - name: wasm
          configMap:
            name: wasm-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: wasm-config
  namespace: ${NS}
data:
  app.wasm: |
    version https://git-lfs.github.com/spec/v1
    oid sha256:1234567890abcdef
    size 1234
---
apiVersion: v1
kind: Service
metadata:
  name: bleater-frontend
  namespace: ${NS}
spec:
  selector:
    app: bleater-frontend
  ports:
    - port: 80
      targetPort: 80
EOF

echo "Saving Deployment UID..."

DEPLOY_UID=$(kubectl get deployment ${DEPLOY} -n ${NS} -o jsonpath='{.metadata.uid}')
mkdir -p /grader
echo "$DEPLOY_UID" > /grader/frontend-deploy-uid

echo "Setup complete."