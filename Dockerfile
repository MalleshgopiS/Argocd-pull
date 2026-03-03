FROM us-central1-docker.pkg.dev/bespokelabs/nebula-devops-registry/nebula-devops:1.0.0

USER root

RUN apt-get update && \
    apt-get install -y git git-lfs curl jq && \
    rm -rf /var/lib/apt/lists/*

RUN git lfs install

WORKDIR /workspace

COPY task.yaml /workspace/task.yaml
COPY setup.sh /workspace/setup.sh
COPY solution.sh /workspace/solution.sh

RUN chmod +x /workspace/setup.sh
RUN chmod +x /workspace/solution.sh

USER ubuntu

CMD ["/bin/bash"]