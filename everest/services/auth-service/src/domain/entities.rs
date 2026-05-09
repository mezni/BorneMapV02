use crate::domain::enums::{InvitationStatus, RegistrationStatus, Source, UserRole, UserStatus};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct User {
    pub user_id: String,
    pub keycloak_id: String,
    pub email: String,
    pub username: String,
    pub first_name: Option<String>,
    pub last_name: Option<String>,
    pub phone: Option<String>,
    pub role: UserRole,
    pub status: UserStatus,
    pub source: Source,
    pub network_id: String,
    pub station_id: String,
    pub last_login_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct UserRegistration {
    pub registration_id: String,
    pub email: String,
    pub username: String,
    pub first_name: Option<String>,
    pub last_name: Option<String>,
    pub phone: Option<String>,
    pub keycloak_id: Option<String>,
    pub verification_token: String,
    pub status: RegistrationStatus,
    pub source: Source,
    pub ip_address: Option<String>,
    pub user_agent: Option<String>,
    pub resend_count: i32,
    pub expires_at: DateTime<Utc>,
    pub verified_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct Invitation {
    pub invitation_id: String,
    pub code: String,
    pub email: String,
    pub role: UserRole,
    pub invited_by: String,
    pub status: InvitationStatus,
    pub metadata: Option<serde_json::Value>,
    pub expires_at: DateTime<Utc>,
    pub accepted_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}
