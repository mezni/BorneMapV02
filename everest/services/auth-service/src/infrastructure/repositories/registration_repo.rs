use crate::core::errors::AppResult;
use crate::domain::entities::UserRegistration;
use crate::domain::repositories::RegistrationRepository;
use async_trait::async_trait;
use chrono::Utc;
use sqlx::PgPool;

pub struct PgRegistrationRepository {
    pool: PgPool,
}

impl PgRegistrationRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl RegistrationRepository for PgRegistrationRepository {
    async fn create(&self, registration: &UserRegistration) -> AppResult<UserRegistration> {
        let result = sqlx::query_as::<_, UserRegistration>(
            r#"
            INSERT INTO user_registrations (
                registration_id, email, username, first_name, last_name, phone,
                keycloak_id, verification_token, status, source, ip_address,
                user_agent, resend_count, expires_at, verified_at, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            RETURNING *
            "#,
        )
        .bind(&registration.registration_id)
        .bind(&registration.email)
        .bind(&registration.username)
        .bind(&registration.first_name)
        .bind(&registration.last_name)
        .bind(&registration.phone)
        .bind(&registration.keycloak_id)
        .bind(&registration.verification_token)
        .bind(&registration.status)
        .bind(&registration.source)
        .bind(&registration.ip_address)
        .bind(&registration.user_agent)
        .bind(&registration.resend_count)
        .bind(&registration.expires_at)
        .bind(&registration.verified_at)
        .bind(&registration.created_at)
        .bind(&registration.updated_at)
        .fetch_one(&self.pool)
        .await?;

        Ok(result)
    }

    async fn find_by_id(&self, registration_id: &str) -> AppResult<Option<UserRegistration>> {
        let result = sqlx::query_as::<_, UserRegistration>(
            "SELECT * FROM user_registrations WHERE registration_id = $1",
        )
        .bind(registration_id)
        .fetch_optional(&self.pool)
        .await?;

        Ok(result)
    }

    async fn find_by_email(&self, email: &str) -> AppResult<Option<UserRegistration>> {
        let result = sqlx::query_as::<_, UserRegistration>(
            "SELECT * FROM user_registrations WHERE email = $1 ORDER BY created_at DESC LIMIT 1",
        )
        .bind(email)
        .fetch_optional(&self.pool)
        .await?;

        Ok(result)
    }

    async fn find_by_token(&self, token: &str) -> AppResult<Option<UserRegistration>> {
        let result = sqlx::query_as::<_, UserRegistration>(
            "SELECT * FROM user_registrations WHERE verification_token = $1",
        )
        .bind(token)
        .fetch_optional(&self.pool)
        .await?;

        Ok(result)
    }

    async fn update(&self, registration: &UserRegistration) -> AppResult<UserRegistration> {
        let result = sqlx::query_as::<_, UserRegistration>(
            r#"
            UPDATE user_registrations SET
                status = $2,
                resend_count = $3,
                verified_at = $4,
                updated_at = $5
            WHERE registration_id = $1
            RETURNING *
            "#,
        )
        .bind(&registration.registration_id)
        .bind(&registration.status)
        .bind(&registration.resend_count)
        .bind(&registration.verified_at)
        .bind(Utc::now())
        .fetch_one(&self.pool)
        .await?;

        Ok(result)
    }
}
