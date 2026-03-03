FROM us-central1-docker.pkg.dev/bespokelabs/nebula-devops-registry/nebula-devops:1.0.0

USER root

# Install only required binary tools
# xxd is required for WASM header validation
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
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

# Default entrypoint
CMD ["/bin/bash", "/setup.sh"]