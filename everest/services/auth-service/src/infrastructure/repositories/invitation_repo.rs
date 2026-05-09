use crate::core::errors::AppResult;
use crate::domain::entities::Invitation;
use crate::domain::repositories::InvitationRepository;
use async_trait::async_trait;
use chrono::Utc;
use sqlx::PgPool;

pub struct PgInvitationRepository {
    pool: PgPool,
}

impl PgInvitationRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl InvitationRepository for PgInvitationRepository {
    async fn create(&self, invitation: &Invitation) -> AppResult<Invitation> {
        let result = sqlx::query_as::<_, Invitation>(
            r#"
            INSERT INTO invitations (
                invitation_id, code, email, role, invited_by, status,
                metadata, expires_at, accepted_at, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING *
            "#,
        )
        .bind(&invitation.invitation_id)
        .bind(&invitation.code)
        .bind(&invitation.email)
        .bind(&invitation.role)
        .bind(&invitation.invited_by)
        .bind(&invitation.status)
        .bind(&invitation.metadata)
        .bind(&invitation.expires_at)
        .bind(&invitation.accepted_at)
        .bind(&invitation.created_at)
        .bind(&invitation.updated_at)
        .fetch_one(&self.pool)
        .await?;

        Ok(result)
    }

    async fn find_by_id(&self, invitation_id: &str) -> AppResult<Option<Invitation>> {
        let result =
            sqlx::query_as::<_, Invitation>("SELECT * FROM invitations WHERE invitation_id = $1")
                .bind(invitation_id)
                .fetch_optional(&self.pool)
                .await?;

        Ok(result)
    }

    async fn find_by_code(&self, code: &str) -> AppResult<Option<Invitation>> {
        let result = sqlx::query_as::<_, Invitation>("SELECT * FROM invitations WHERE code = $1")
            .bind(code)
            .fetch_optional(&self.pool)
            .await?;

        Ok(result)
    }

    async fn find_by_email(&self, email: &str) -> AppResult<Vec<Invitation>> {
        let results = sqlx::query_as::<_, Invitation>(
            "SELECT * FROM invitations WHERE email = $1 ORDER BY created_at DESC",
        )
        .bind(email)
        .fetch_all(&self.pool)
        .await?;

        Ok(results)
    }

    async fn list(&self, limit: i64, offset: i64) -> AppResult<Vec<Invitation>> {
        let results = sqlx::query_as::<_, Invitation>(
            "SELECT * FROM invitations ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        )
        .bind(limit)
        .bind(offset)
        .fetch_all(&self.pool)
        .await?;

        Ok(results)
    }

    async fn update(&self, invitation: &Invitation) -> AppResult<Invitation> {
        let result = sqlx::query_as::<_, Invitation>(
            r#"
            UPDATE invitations SET
                status = $2,
                accepted_at = $3,
                updated_at = $4
            WHERE invitation_id = $1
            RETURNING *
            "#,
        )
        .bind(&invitation.invitation_id)
        .bind(&invitation.status)
        .bind(&invitation.accepted_at)
        .bind(Utc::now())
        .fetch_one(&self.pool)
        .await?;

        Ok(result)
    }

    async fn delete(&self, invitation_id: &str) -> AppResult<()> {
        sqlx::query("DELETE FROM invitations WHERE invitation_id = $1")
            .bind(invitation_id)
            .execute(&self.pool)
            .await?;

        Ok(())
    }
}
