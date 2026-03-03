#!/bin/bash
cd /data/repo
# 1. Configure attributes to force LFS tracking
echo "*.wasm filter=lfs diff=lfs merge=lfs -text" > .gitattributes
git add .gitattributes
git lfs track "*.wasm"
git commit -m "Fix LFS tracking for WASM"
# 2. Sync ArgoCD to apply changes
argocd app sync bleater-ui