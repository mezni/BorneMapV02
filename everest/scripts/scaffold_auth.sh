#!/bin/bash

cargo new auth_service

# Create main directories
mkdir -p auth_service/src/{application,core,domain,infrastructure,presentation}
mkdir -p auth_service/src/application/dtos
mkdir -p auth_service/src/core
mkdir -p auth_service/src/domain
mkdir -p auth_service/src/infrastructure/repositories
mkdir -p auth_service/src/presentation/controllers

# Create files
touch auth_service/src/main.rs
touch auth_service/src/lib.rs
touch auth_service/src/bin/cleanup_job.rs
touch auth_service/Cargo.toml
touch auth_service/.env
touch auth_service/schema.sql
touch auth_service/docker-compose.yml
touch auth_service/README.md

# Application layer
touch auth_service/src/application/{mod.rs,admin_service.rs,authentication_service.rs,health_service.rs,invitation_service.rs,registration_service.rs}

# DTOs
touch auth_service/src/application/dtos/{mod.rs,admin.rs,authentication.rs,health.rs,invitation.rs,registration.rs}

# Core utilities
touch auth_service/src/core/{mod.rs,auth.rs,config.rs,constants.rs,database.rs,errors.rs,logging.rs,utils.rs}

# Domain layer
touch auth_service/src/domain/{mod.rs,entities.rs,enums.rs,repositories.rs,services.rs,value_objects.rs}

# Infrastructure layer
touch auth_service/src/infrastructure/{mod.rs,keycloak_client.rs}
touch auth_service/src/infrastructure/repositories/{mod.rs,user_repo.rs,registration_repo.rs,invitation_repo.rs}

# Presentation layer
touch auth_service/src/presentation/{mod.rs,openapi.rs}
touch auth_service/src/presentation/controllers/{mod.rs,admin_controller.rs,authentication_controller.rs,health_controller.rs,invitation_controller.rs,registration_controller.rs}