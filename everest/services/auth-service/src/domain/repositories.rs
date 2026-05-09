use super::entities::{Invitation, User, UserRegistration};
use crate::core::errors::AppResult;
use async_trait::async_trait;

#[async_trait]
pub trait UserRepository: Send + Sync {
    async fn create(&self, user: &User) -> AppResult<User>;
    async fn find_by_id(&self, user_id: &str) -> AppResult<Option<User>>;
    async fn find_by_email(&self, email: &str) -> AppResult<Option<User>>;
    async fn find_by_keycloak_id(&self, keycloak_id: &str) -> AppResult<Option<User>>;
    async fn update(&self, user: &User) -> AppResult<User>;
    async fn update_last_login(&self, user_id: &str) -> AppResult<()>;
    async fn list_active(&self, limit: i64, offset: i64) -> AppResult<Vec<User>>;
    async fn count_active(&self, network_id: Option<&str>) -> AppResult<i64>;
}

#[async_trait]
pub trait RegistrationRepository: Send + Sync {
    async fn create(&self, registration: &UserRegistration) -> AppResult<UserRegistration>;
    async fn find_by_id(&self, registration_id: &str) -> AppResult<Option<UserRegistration>>;
    async fn find_by_email(&self, email: &str) -> AppResult<Option<UserRegistration>>;
    async fn find_by_token(&self, token: &str) -> AppResult<Option<UserRegistration>>;
    async fn update(&self, registration: &UserRegistration) -> AppResult<UserRegistration>;
}

#[async_trait]
pub trait InvitationRepository: Send + Sync {
    async fn create(&self, invitation: &Invitation) -> AppResult<Invitation>;
    async fn find_by_id(&self, invitation_id: &str) -> AppResult<Option<Invitation>>;
    async fn find_by_code(&self, code: &str) -> AppResult<Option<Invitation>>;
    async fn find_by_email(&self, email: &str) -> AppResult<Vec<Invitation>>;
    async fn list(&self, limit: i64, offset: i64) -> AppResult<Vec<Invitation>>;
    async fn update(&self, invitation: &Invitation) -> AppResult<Invitation>;
    async fn delete(&self, invitation_id: &str) -> AppResult<()>;
}
