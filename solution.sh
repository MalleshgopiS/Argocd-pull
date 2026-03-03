#!/bin/bash
set -e

cd /workspace/repo

git lfs checkout

kubectl rollout restart deployment bleater-frontend -n bleater
kubectl rollout status deployment bleater-frontend -n bleater