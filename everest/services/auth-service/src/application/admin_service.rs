use crate::core::constants::*;
use crate::core::errors::{AppError, AppResult};
use crate::core::utils::generate_id;
use crate::domain::entities::User;
use crate::domain::enums::{Source, UserRole, UserStatus};
use crate::domain::repositories::UserRepository;
use crate::domain::services::AdminService;
use crate::domain::value_objects::{CreateUserData, UpdateUserData};
use crate::infrastructure::keycloak_client::KeycloakClient;
use async_trait::async_trait;
use chrono::Utc;
use std::collections::HashMap;
use std::sync::Arc;

pub struct AdminServiceImpl {
    user_repo: Arc<dyn UserRepository>,
    keycloak: Arc<dyn KeycloakClient>,
}

impl AdminServiceImpl {
    pub fn new(user_repo: Arc<dyn UserRepository>, keycloak: Arc<dyn KeycloakClient>) -> Self {
        Self {
            user_repo,
            keycloak,
        }
    }
}

#[async_trait]
impl AdminService for AdminServiceImpl {
    async fn list_users(&self, limit: i64, offset: i64) -> AppResult<(Vec<User>, i64)> {
        let users = self.user_repo.list_active(limit, offset).await?;
        let total = self.user_repo.count_active(None).await?;
        Ok((users, total))
    }

    async fn get_user(&self, user_id: &str) -> AppResult<User> {
        self.user_repo
            .find_by_id(user_id)
            .await?
            .ok_or(AppError::NotFound("User not found".to_string()))
    }

    async fn create_user(&self, user_data: CreateUserData) -> AppResult<User> {
        // Check for existing user
        if self
            .user_repo
            .find_by_email(&user_data.email)
            .await?
            .is_some()
        {
            return Err(AppError::Conflict("Email already exists".to_string()));
        }

        // Parse role
        let role = UserRole::from_str(&user_data.role)
            .ok_or(AppError::ValidationError("Invalid role".to_string()))?;

        // Setup attributes
        let mut attributes = HashMap::new();
        attributes.insert(
            "network_id".to_string(),
            vec![user_data
                .network_id
                .clone()
                .unwrap_or_else(|| DEFAULT_NETWORK_ID.to_string())],
        );
        attributes.insert(
            "station_id".to_string(),
            vec![user_data
                .station_id
                .clone()
                .unwrap_or_else(|| DEFAULT_STATION_ID.to_string())],
        );

        // Create in Keycloak
        let keycloak_id = self
            .keycloak
            .create_user(
                &user_data.email,
                &user_data.username,
                &user_data.password,
                Some(attributes),
            )
            .await?;

        // Assign role
        self.keycloak
            .assign_role(&keycloak_id, &user_data.role)
            .await?;

        // Create user record
        let user = User {
            user_id: generate_id(USER_ID_PREFIX),
            keycloak_id,
            email: user_data.email,
            username: user_data.username,
            first_name: user_data.first_name,
            last_name: user_data.last_name,
            phone: user_data.phone,
            role,
            status: UserStatus::Active,
            source: Source::Admin,
            network_id: user_data
                .network_id
                .unwrap_or_else(|| DEFAULT_NETWORK_ID.to_string()),
            station_id: user_data
                .station_id
                .unwrap_or_else(|| DEFAULT_STATION_ID.to_string()),
            last_login_at: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        self.user_repo.create(&user).await
    }

    async fn update_user(&self, user_id: &str, user_data: UpdateUserData) -> AppResult<User> {
        let mut user = self
            .user_repo
            .find_by_id(user_id)
            .await?
            .ok_or(AppError::NotFound("User not found".to_string()))?;

        // Update email if provided
        if let Some(email) = user_data.email {
            user.email = email;
        }

        // Update role if provided
        if let Some(role_str) = user_data.role {
            let role = UserRole::from_str(&role_str)
                .ok_or(AppError::ValidationError("Invalid role".to_string()))?;
            user.role = role;

            // Update in Keycloak
            self.keycloak
                .assign_role(&user.keycloak_id, &role_str)
                .await?;
        }

        // Update enabled status if provided
        if let Some(enabled) = user_data.enabled {
            if enabled {
                self.keycloak.enable_user(&user.keycloak_id).await?;
                user.status = UserStatus::Active;
            } else {
                self.keycloak.disable_user(&user.keycloak_id).await?;
                user.status = UserStatus::Inactive;
            }
        }

        user.updated_at = Utc::now();
        self.user_repo.update(&user).await
    }

    async fn delete_user(&self, user_id: &str) -> AppResult<()> {
        let mut user = self
            .user_repo
            .find_by_id(user_id)
            .await?
            .ok_or(AppError::NotFound("User not found".to_string()))?;

        // Soft delete - disable in Keycloak
        self.keycloak.disable_user(&user.keycloak_id).await?;

        // Update status
        user.status = UserStatus::Deleted;
        user.updated_at = Utc::now();
        self.user_repo.update(&user).await?;

        Ok(())
    }
}
