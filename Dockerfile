FROM us-central1-docker.pkg.dev/bespokelabs/nebula-devops-registry/nebula-devops:1.0.0

USER root

# Install minimal required tools
# jq: JSON parsing
# xxd: validate WASM header
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        jq=1.6* \
        xxd \
    && rm -rf /var/lib/apt/lists/*

# Ensure grader directory exists
RUN mkdir -p /grader

# Copy task files
COPY setup.sh /setup.sh
COPY solution.sh /solution.sh
COPY grader.py /grader/grader.py

# Ensure executables
RUN chmod +x /setup.sh /solution.sh

# Default entrypoint runs setup
CMD ["/bin/bash", "/setup.sh"]