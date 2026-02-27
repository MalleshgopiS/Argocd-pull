# Validation Specification — ArgoCD Git LFS Debugging

## Overview

The grader validates that ArgoCD retrieves real Git LFS binary artifacts
instead of pointer files.

All validations are performed against live Kubernetes state.

## Validation Checks

1. WASM file size must exceed 10KB (binary verification).
2. Deployment must become Ready.
3. Deployment UID must match stored UID.
4. argocd-repo-server must contain:
   ARGOCD_GIT_LFS_ENABLED=true
5. Service endpoints must exist.

## Anti-Cheating

- Pod filesystem inspected directly.
- Binary size validation prevents fake fixes.
- Repo-server restart required.
- UID preservation enforced.

## Scoring

score = passed_checks / total_checks