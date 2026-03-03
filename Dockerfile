FROM us-central1-docker.pkg.dev/bespokelabs/nebula-devops-registry/nebula-devops:1.0.0

USER root

# Required tools:
# jq  - JSON parsing
# xxd - WASM header validation
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        jq=1.6-2.1ubuntu3 \
        xxd \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /grader

COPY setup.sh /setup.sh
COPY solution.sh /solution.sh
COPY grader.py /grader/grader.py

RUN chmod +x /setup.sh /solution.sh

CMD ["/bin/bash", "/setup.sh"]