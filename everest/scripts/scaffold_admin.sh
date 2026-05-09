#!/bin/bash

# Create project directory
cargo new admin-service

# Create subdirectories
mkdir -p admin-service/src/core
mkdir -p admin-service/src/domain
mkdir -p admin-service/src/domain/value_objects
mkdir -p admin-service/src/infrastructure/repositories
mkdir -p admin-service/src/application/dtos
mkdir -p admin-service/src/presentation/controllers

# Create empty files
touch admin-service/Cargo.toml
touch admin-service/.env
touch admin-service/docker-compose.yml
touch admin-service/schema.sql
touch admin-service/README.md

touch admin-service/src/main.rs
touch admin-service/src/lib.rs

touch admin-service/src/core/mod.rs
touch admin-service/src/core/auth.rs
touch admin-service/src/core/config.rs
touch admin-service/src/core/constants.rs
touch admin-service/src/core/database.rs
touch admin-service/src/core/errors.rs
touch admin-service/src/core/logging.rs
touch admin-service/src/core/utils.rs

touch admin-service/src/domain/mod.rs
touch admin-service/src/domain/entities.rs
touch admin-service/src/domain/repositories.rs
touch admin-service/src/domain/services.rs
touch admin-service/src/domain/value_objects/mod.rs

touch admin-service/src/infrastructure/mod.rs
touch admin-service/src/infrastructure/repositories/mod.rs
touch admin-service/src/infrastructure/repositories/network_repo.rs
touch admin-service/src/infrastructure/repositories/station_repo.rs
touch admin-service/src/infrastructure/repositories/connector_repo.rs

touch admin-service/src/application/mod.rs
touch admin-service/src/application/network_service.rs
touch admin-service/src/application/station_service.rs
touch admin-service/src/application/connector_service.rs
touch admin-service/src/application/dtos/mod.rs
touch admin-service/src/application/dtos/network.rs
touch admin-service/src/application/dtos/station.rs
touch admin-service/src/application/dtos/connector.rs

touch admin-service/src/presentation/mod.rs
touch admin-service/src/presentation/controllers/mod.rs
touch admin-service/src/presentation/controllers/network_controller.rs
touch admin-service/src/presentation/controllers/station_controller.rs
touch admin-service/src/presentation/controllers/connector_controller.rs