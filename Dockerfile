FROM us-central1-docker.pkg.dev/bespokelabs/nebula-devops-registry/nebula-devops:1.0.0
WORKDIR /workspace
COPY setup.sh /workspace/setup.sh
RUN chmod +x /workspace/setup.sh