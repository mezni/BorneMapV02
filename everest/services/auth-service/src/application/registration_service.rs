use crate::core::constants::*;
use crate::core::errors::{AppError, AppResult};
use crate::core::utils::{generate_id, generate_token};
use crate::domain::entities::{User, UserRegistration};
use crate::domain::enums::{RegistrationStatus, Source, UserRole, UserStatus};
use crate::domain::repositories::{RegistrationRepository, UserRepository};
use crate::domain::services::RegistrationService;
use crate::infrastructure::keycloak_client::KeycloakClient;
use async_trait::async_trait;
use chrono::Utc;
use std::collections::HashMap;
use std::sync::Arc;

pub struct RegistrationServiceImpl {
    user_repo: Arc<dyn UserRepository>,
    reg_repo: Arc<dyn RegistrationRepository>,
    keycloak: Arc<dyn KeycloakClient>,
}

impl RegistrationServiceImpl {
    pub fn new(
        user_repo: Arc<dyn UserRepository>,
        reg_repo: Arc<dyn RegistrationRepository>,
        keycloak: Arc<dyn KeycloakClient>,
    ) -> Self {
        Self {
            user_repo,
            reg_repo,
            keycloak,
        }
    }
}

#[async_trait]
impl RegistrationService for RegistrationServiceImpl {
    async fn register(
        &self,
        email: String,
        username: String,
        password: String,
        first_name: Option<String>,
        last_name: Option<String>,
        phone: Option<String>,
        source: Source,
        ip_address: Option<String>,
        user_agent: Option<String>,
    ) -> AppResult<UserRegistration> {
        // Check for existing user or registration
        if self.user_repo.find_by_email(&email).await?.is_some() {
            return Err(AppError::Conflict("Email already registered".to_string()));
        }

        if self.reg_repo.find_by_email(&email).await?.is_some() {
            return Err(AppError::Conflict(
                "Registration already pending".to_string(),
            ));
        }

        // Create user in Keycloak (disabled initially)
        let mut attributes = HashMap::new();
        attributes.insert(
            "network_id".to_string(),
            vec![DEFAULT_NETWORK_ID.to_string()],
        );
        attributes.insert(
            "station_id".to_string(),
            vec![DEFAULT_STATION_ID.to_string()],
        );

        let keycloak_id = self
            .keycloak
            .create_user(&email, &username, &password, Some(attributes))
            .await?;

        // Disable and unverify the user
        self.keycloak.disable_user(&keycloak_id).await?;

        // Send verification email
        //        self.keycloak.send_verification_email(&keycloak_id).await?;

        // Create registration record
        let registration = UserRegistration {
            registration_id: generate_id(REGISTRATION_ID_PREFIX),
            email,
            username,
            first_name,
            last_name,
            phone,
            keycloak_id: Some(keycloak_id),
            verification_token: generate_token(VERIFICATION_TOKEN_LENGTH),
            status: RegistrationStatus::Pending,
            source,
            ip_address,
            user_agent,
            resend_count: 0,
            expires_at: Utc::now() + chrono::Duration::hours(VERIFICATION_EXPIRY_HOURS),
            verified_at: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        self.reg_repo.create(&registration).await
    }

    async fn verify(&self, email: String, token: String) -> AppResult<User> {
        let mut registration = self
            .reg_repo
            .find_by_email(&email)
            .await?
            .ok_or(AppError::NotFound("Registration not found".to_string()))?;

        // Check token
        if registration.verification_token != token {
            return Err(AppError::VerificationInvalid);
        }

        // Check expiry
        if Utc::now() > registration.expires_at {
            registration.status = RegistrationStatus::VerificationExpired;
            self.reg_repo.update(&registration).await?;

            // Delete from Keycloak
            if let Some(ref keycloak_id) = registration.keycloak_id {
                let _ = self.keycloak.delete_user(keycloak_id).await;
            }

            return Err(AppError::VerificationExpired);
        }

        let keycloak_id = registration
            .keycloak_id
            .as_ref()
            .ok_or(AppError::InternalError("Missing Keycloak ID".to_string()))?;

        // Enable user in Keycloak
        self.keycloak.enable_user(keycloak_id).await?;

        // Assign default role
        self.keycloak.assign_role(keycloak_id, ROLE_USER).await?;

        // Create user record
        let user = User {
            user_id: generate_id(USER_ID_PREFIX),
            keycloak_id: keycloak_id.clone(),
            email: registration.email.clone(),
            username: registration.username.clone(),
            first_name: registration.first_name.clone(),
            last_name: registration.last_name.clone(),
            phone: registration.phone.clone(),
            role: UserRole::User,
            status: UserStatus::Active,
            source: registration.source,
            network_id: DEFAULT_NETWORK_ID.to_string(),
            station_id: DEFAULT_STATION_ID.to_string(),
            last_login_at: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        let created_user = self.user_repo.create(&user).await?;

        // Update registration status
        registration.status = RegistrationStatus::Active;
        registration.verified_at = Some(Utc::now());
        registration.updated_at = Utc::now();
        self.reg_repo.update(&registration).await?;

        Ok(created_user)
    }

    async fn resend_verification(&self, email: String) -> AppResult<()> {
        let mut registration = self
            .reg_repo
            .find_by_email(&email)
            .await?
            .ok_or(AppError::NotFound("Registration not found".to_string()))?;

        if registration.status != RegistrationStatus::Pending {
            return Err(AppError::ValidationError(
                "Registration not in pending state".to_string(),
            ));
        }

        if registration.resend_count >= MAX_RESEND_ATTEMPTS {
            return Err(AppError::ResendLimitExceeded);
        }

        let keycloak_id = registration
            .keycloak_id
            .as_ref()
            .ok_or(AppError::InternalError("Missing Keycloak ID".to_string()))?;

        // Resend verification email
        self.keycloak.send_verification_email(keycloak_id).await?;

        // Update resend count
        registration.resend_count += 1;
        registration.updated_at = Utc::now();
        self.reg_repo.update(&registration).await?;

        Ok(())
    }
}
