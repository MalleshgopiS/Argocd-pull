FROM us-central1-docker.pkg.dev/bespokelabs/nebula-devops-registry/nebula-devops:1.0.0
# Ensure LFS is present in the environment
RUN apt-get update && apt-get install -y git-lfs && rm -rf /var/lib/apt/lists/*