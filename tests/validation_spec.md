# Validation Specification — ArgoCD Git LFS Debugging

## Overview

The grader validates that ArgoCD retrieves Git LFS binary artifacts
instead of Git LFS pointer files.

All checks use live Kubernetes cluster state.

## Validation Checks

1. WASM file does NOT contain:
   version https://git-lfs.github.com/spec/v1

2. Deployment has ready replicas.

3. Deployment UID matches original stored value.

4. argocd-repo-server contains:
   ARGOCD_GIT_LFS_ENABLED=true

5. Service endpoints are non-empty.

## Scoring

score = passed_checks / total_checks