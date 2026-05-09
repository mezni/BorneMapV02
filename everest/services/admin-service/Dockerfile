# Stage 1: The Cached Base Layer (System dependencies and common Rust crates)
FROM rust:1.90-slim-bullseye AS rust-base-builder


# Install build-time system dependencies and packages
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libpq-dev \
    curl \
    # Add other common build dependencies here
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a dummy Cargo.toml with common dependencies to leverage Docker caching
RUN echo '[package]' > Cargo.toml \
    && echo 'name = "base_cache"' >> Cargo.toml \
    && echo 'version = "0.1.0"' >> Cargo.toml \
    && echo 'edition = "2021"' >> Cargo.toml \
    && echo 'authors = ["M.MEZNI"]' >> Cargo.toml \
    && echo 'description = "Bornemap"' >> Cargo.toml \
    && echo '[dependencies]' >> Cargo.toml \
    # List common dependencies that are slow to compile
    && echo 'actix-web = "4.12.1"' >> Cargo.toml \
    && echo 'actix-cors = "0.7.1"' >> Cargo.toml \
    && echo 'tokio = { version = "1.48.0", features = ["full"] }' >> Cargo.toml \
    && echo 'sqlx = { version = "0.8.6", features = ["runtime-tokio-rustls", "postgres", "uuid", "chrono", "json"] }' >> Cargo.toml \
    && echo 'serde = { version = "1.0.228", features = ["derive"] }' >> Cargo.toml \
    && echo 'serde_json = "1.0.145"' >> Cargo.toml \
    && echo 'anyhow = "1.0.100"' >> Cargo.toml \
    && echo 'thiserror = "2.0.17"' >> Cargo.toml \
    && echo 'tracing = "0.1.43"' >> Cargo.toml \
    && echo 'tracing-subscriber = { version = "0.3.22", features = ["env-filter", "json"] }' >> Cargo.toml \
    && echo 'tracing-actix-web = "0.7.20"' >> Cargo.toml \
    && echo 'dotenvy = "0.15.7"' >> Cargo.toml \
    && echo 'utoipa = { version = "5.4.0", features = ["actix_extras", "chrono", "uuid"] }' >> Cargo.toml \
    && echo 'utoipa-swagger-ui = { version = "9.0.2", features = ["actix-web"] }' >> Cargo.toml \
    # Compile common dependencies to populate the target cache
    && mkdir src \
    && echo 'fn main() { println!("Base cache build"); }' > src/main.rs \
    && cargo build --release \
    # Clean up the manifest and source files, keeping the compiled dependencies
    && rm -rf Cargo.toml Cargo.lock src target/release/base_cache

# Stage 2: Build the Application (FAST build stage)
FROM rust-base-builder AS builder

WORKDIR /app

# Copy the service-specific manifest files (Actix is already cached)
COPY Cargo.toml Cargo.lock ./

# Copy the source code
COPY . .

# Build the application (fast because common dependencies are cached)
RUN cargo build --release

# Stage 3: Create the Final Slim Image (Runtime)
FROM debian:bullseye-slim 

# Install runtime dependencies and set up a non-root user
ARG UID=1001

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libssl1.1 \
    passwd \
    # Create a non-root user
    && useradd -m -u $UID appuser \
    # Clean up package list files
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the compiled binary from the builder
COPY --from=builder /app/target/release/admin-service /app/admin-service

# Set ownership and permissions
RUN chown -R appuser:appuser /app

USER appuser

# Expose the application port
EXPOSE 3000

# Health check to verify the application is running
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Run the application
CMD ["./admin-service"]