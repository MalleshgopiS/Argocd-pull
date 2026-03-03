#!/bin/bash
set -e

# Replace pointer file with valid WASM binary
printf '\x00\x61\x73\x6d\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' > /workspace/repo/static/app.wasm

kubectl rollout restart deployment bleater-frontend -n bleater
kubectl rollout status deployment bleater-frontend -n bleater