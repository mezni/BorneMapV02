FROM debian:bookworm-backports

ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && \
    apt-get install -y \
        curl \
        osm2pgsql/bookworm-backports \
        postgresql-client-15 \
        osmctools \
        bash \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy scripts and style file
COPY ./osm-importer.sh /usr/local/bin/osm-importer.sh
COPY ./custom.style /usr/local/bin/custom.style

# Make the script executable
RUN chmod +x /usr/local/bin/osm-importer.sh

# Set working directory inside the container
WORKDIR /osm

# Set default entrypoint to the importer script
ENTRYPOINT ["/usr/local/bin/osm-importer.sh"]