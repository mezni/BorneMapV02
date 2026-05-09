use crate::core::constants::*;
use crate::core::errors::{AppError, AppResult};
use crate::core::utils::{generate_code, generate_id};
use crate::domain::entities::{Invitation, User};
use crate::domain::enums::{InvitationStatus, Source, UserRole, UserStatus};
use crate::domain::repositories::{InvitationRepository, UserRepository};
use crate::domain::services::InvitationService;
use crate::infrastructure::keycloak_client::KeycloakClient;
use async_trait::async_trait;
use chrono::Utc;
use std::collections::HashMap;
use std::sync::Arc;

pub struct InvitationServiceImpl {
    invitation_repo: Arc<dyn InvitationRepository>,
    user_repo: Arc<dyn UserRepository>,
    keycloak: Arc<dyn KeycloakClient>,
}

impl InvitationServiceImpl {
    pub fn new(
        invitation_repo: Arc<dyn InvitationRepository>,
        user_repo: Arc<dyn UserRepository>,
        keycloak: Arc<dyn KeycloakClient>,
    ) -> Self {
        Self {
            invitation_repo,
            user_repo,
            keycloak,
        }
    }
}

#[async_trait]
impl InvitationService for InvitationServiceImpl {
    async fn create_invitation(
        &self,
        email: String,
        role: String,
        invited_by: String,
        expires_in_hours: i64,
        metadata: Option<serde_json::Value>,
    ) -> AppResult<Invitation> {
        // Validate role
        let user_role = UserRole::from_str(&role)
            .ok_or(AppError::ValidationError("Invalid role".to_string()))?;

        let invitation = Invitation {
            invitation_id: generate_id(INVITATION_ID_PREFIX),
            code: generate_code(INVITATION_CODE_LENGTH),
            email,
            role: user_role,
            invited_by,
            status: InvitationStatus::Pending,
            metadata,
            expires_at: Utc::now() + chrono::Duration::hours(expires_in_hours),
            accepted_at: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        self.invitation_repo.create(&invitation).await
    }

    async fn list_invitations(&self, limit: i64, offset: i64) -> AppResult<Vec<Invitation>> {
        self.invitation_repo.list(limit, offset).await
    }

    async fn get_invitation(&self, code: String) -> AppResult<Invitation> {
        let invitation = self
            .invitation_repo
            .find_by_code(&code)
            .await?
            .ok_or(AppError::InvitationInvalid)?;

        if Utc::now() > invitation.expires_at {
            return Err(AppError::InvitationExpired);
        }

        if invitation.status != InvitationStatus::Pending {
            return Err(AppError::InvitationInvalid);
        }

        Ok(invitation)
    }

    async fn accept_invitation(&self, code: String, password: String) -> AppResult<User> {
        let mut invitation = self.get_invitation(code).await?;

        // Check if user already exists
        if self
            .user_repo
            .find_by_email(&invitation.email)
            .await?
            .is_some()
        {
            return Err(AppError::Conflict("Email already registered".to_string()));
        }

        // Generate username from email
        let username = invitation
            .email
            .split('@')
            .next()
            .unwrap_or("user")
            .to_string();

        // Setup attributes
        let mut attributes = HashMap::new();
        attributes.insert(
            "network_id".to_string(),
            vec![DEFAULT_NETWORK_ID.to_string()],
        );
        attributes.insert(
            "station_id".to_string(),
            vec![DEFAULT_STATION_ID.to_string()],
        );

        // Create in Keycloak
        let keycloak_id = self
            .keycloak
            .create_user(&invitation.email, &username, &password, Some(attributes))
            .await?;

        // Assign role
        self.keycloak
            .assign_role(&keycloak_id, &invitation.role.to_string())
            .await?;

        // Create user
        let user = User {
            user_id: generate_id(USER_ID_PREFIX),
            keycloak_id,
            email: invitation.email.clone(),
            username,
            first_name: None,
            last_name: None,
            phone: None,
            role: invitation.role,
            status: UserStatus::Active,
            source: Source::Invitation,
            network_id: DEFAULT_NETWORK_ID.to_string(),
            station_id: DEFAULT_STATION_ID.to_string(),
            last_login_at: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        let created_user = self.user_repo.create(&user).await?;

        // Update invitation
        invitation.status = InvitationStatus::Accepted;
        invitation.accepted_at = Some(Utc::now());
        invitation.updated_at = Utc::now();
        self.invitation_repo.update(&invitation).await?;

        Ok(created_user)
    }

    async fn cancel_invitation(&self, code: String) -> AppResult<()> {
        let mut invitation = self
            .invitation_repo
            .find_by_code(&code)
            .await?
            .ok_or(AppError::NotFound("Invitation not found".to_string()))?;

        invitation.status = InvitationStatus::Cancelled;
        invitation.updated_at = Utc::now();
        self.invitation_repo.update(&invitation).await?;

        Ok(())
    }
}
