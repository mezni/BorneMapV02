use crate::application::dtos::authentication::ValidateResponse;
use crate::core::errors::{AppError, AppResult};
use crate::domain::repositories::UserRepository;
use crate::domain::services::AuthenticationService;
use crate::domain::value_objects::LoginResponse;
use crate::infrastructure::keycloak_client::KeycloakClient;
use async_trait::async_trait;
use std::sync::Arc;

pub struct AuthenticationServiceImpl {
    user_repo: Arc<dyn UserRepository>,
    keycloak: Arc<dyn KeycloakClient>,
}

impl AuthenticationServiceImpl {
    pub fn new(user_repo: Arc<dyn UserRepository>, keycloak: Arc<dyn KeycloakClient>) -> Self {
        Self {
            user_repo,
            keycloak,
        }
    }

    pub async fn validate_token(&self, access_token: String) -> AppResult<ValidateResponse> {
        let token_info = self.keycloak.verify_token(&access_token).await?;

        Ok(ValidateResponse {
            active: token_info["active"].as_bool().unwrap_or(false),
            sub: token_info["sub"].as_str().unwrap_or_default().to_string(),
            username: token_info["preferred_username"]
                .as_str()
                .map(|s| s.to_string()),
            roles: token_info["roles"]
                .as_array()
                .map(|arr| {
                    arr.iter()
                        .filter_map(|v| v.as_str().map(|s| s.to_string()))
                        .collect()
                })
                .unwrap_or_default(),
            exp: token_info["exp"].as_i64().unwrap_or(0),
        })
    }
}

#[async_trait]
impl AuthenticationService for AuthenticationServiceImpl {
    async fn login(&self, username: String, password: String) -> AppResult<LoginResponse> {
        // Authenticate with Keycloak
        let token_response = self.keycloak.authenticate(&username, &password).await?;

        // Get user info
        let user_info = self
            .keycloak
            .get_user_info(&token_response.access_token)
            .await?;

        let keycloak_id = user_info["sub"]
            .as_str()
            .ok_or(AppError::InternalError("Missing user ID".to_string()))?;

        // Update last login
        if let Some(user) = self.user_repo.find_by_keycloak_id(keycloak_id).await? {
            let _ = self.user_repo.update_last_login(&user.user_id).await;
        }

        Ok(LoginResponse {
            access_token: token_response.access_token,
            refresh_token: token_response.refresh_token,
            token_type: token_response.token_type,
            expires_in: token_response.expires_in,
            refresh_expires_in: token_response.refresh_expires_in,
        })
    }

    async fn logout(&self, refresh_token: String) -> AppResult<()> {
        self.keycloak.logout(&refresh_token).await?;
        Ok(())
    }

    async fn refresh_token(&self, refresh_token: String) -> AppResult<LoginResponse> {
        let token_response = self.keycloak.refresh_token(&refresh_token).await?;

        Ok(LoginResponse {
            access_token: token_response.access_token,
            refresh_token: token_response.refresh_token,
            token_type: token_response.token_type,
            expires_in: token_response.expires_in,
            refresh_expires_in: token_response.refresh_expires_in,
        })
    }
}
