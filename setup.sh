#!/usr/bin/env bash
set -euo pipefail

echo "========================================"
echo "ArgoCD Git LFS Broken Task Setup"
echo "========================================"

NS="bleater"
APP="bleater-frontend"

echo "Creating namespace..."
kubectl create namespace ${NS} --dry-run=client -o yaml | kubectl apply -f -

echo "Grant ubuntu-user access to argocd..."
kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ubuntu-user-argocd-admin
  namespace: argocd
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
EOF

kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ubuntu-user-argocd-admin-binding
  namespace: argocd
subjects:
- kind: User
  name: ubuntu-user
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: ubuntu-user-argocd-admin
  apiGroup: rbac.authorization.k8s.io
EOF

echo "Creating broken WASM ConfigMap..."

kubectl apply -n ${NS} -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: wasm-config
data:
  app.wasm: |
    version https://git-lfs.github.com/spec/v1
    oid sha256:deadbeef
    size 123
EOF

echo "Deploying broken frontend..."

kubectl apply -n ${NS} -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${APP}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${APP}
  template:
    metadata:
      labels:
        app: ${APP}
    spec:
      containers:
      - name: frontend
        image: nginx:1.25
        command: ["/bin/sh","-c"]
        args:
          - mkdir -p /usr/share/nginx/html;
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

kubectl apply -n ${NS} -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: ${APP}
spec:
  selector:
    app: ${APP}
  ports:
  - port: 80
    targetPort: 80
EOF

echo "Saving Deployment UID for grader..."

# ✅ FIXED PART
mkdir -p /grader

UID=$(kubectl get deploy ${APP} -n ${NS} -o jsonpath='{.metadata.uid}')
echo "$UID" > /grader/frontend-deploy-uid

echo "Setup complete."