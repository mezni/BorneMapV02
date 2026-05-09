use crate::core::errors::AppResult;
use crate::domain::entities::{Invitation, User, UserRegistration};
use crate::domain::enums::Source;
use crate::domain::value_objects::{CreateUserData, LoginResponse, UpdateUserData};
use async_trait::async_trait;

#[async_trait]
pub trait RegistrationService: Send + Sync {
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
    ) -> AppResult<UserRegistration>;

    async fn verify(&self, email: String, token: String) -> AppResult<User>;
    async fn resend_verification(&self, email: String) -> AppResult<()>;
}

#[async_trait]
pub trait AuthenticationService: Send + Sync {
    async fn login(&self, username: String, password: String) -> AppResult<LoginResponse>;
    async fn logout(&self, refresh_token: String) -> AppResult<()>;
    async fn refresh_token(&self, refresh_token: String) -> AppResult<LoginResponse>;
}

#[async_trait]
pub trait AdminService: Send + Sync {
    async fn list_users(&self, limit: i64, offset: i64) -> AppResult<(Vec<User>, i64)>;
    async fn get_user(&self, user_id: &str) -> AppResult<User>;
    async fn create_user(&self, user_data: CreateUserData) -> AppResult<User>;
    async fn update_user(&self, user_id: &str, user_data: UpdateUserData) -> AppResult<User>;
    async fn delete_user(&self, user_id: &str) -> AppResult<()>;
}

#[async_trait]
pub trait InvitationService: Send + Sync {
    async fn create_invitation(
        &self,
        email: String,
        role: String,
        invited_by: String,
        expires_in_hours: i64,
        metadata: Option<serde_json::Value>,
    ) -> AppResult<Invitation>;

    async fn list_invitations(&self, limit: i64, offset: i64) -> AppResult<Vec<Invitation>>;
    async fn get_invitation(&self, code: String) -> AppResult<Invitation>;
    async fn accept_invitation(&self, code: String, password: String) -> AppResult<User>;
    async fn cancel_invitation(&self, code: String) -> AppResult<()>;
}
