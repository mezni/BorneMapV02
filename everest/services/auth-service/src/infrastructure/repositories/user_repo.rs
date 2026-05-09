use crate::core::errors::AppResult;
use crate::domain::entities::User;
use crate::domain::repositories::UserRepository;
use async_trait::async_trait;
use chrono::Utc;
use sqlx::PgPool;

pub struct PgUserRepository {
    pool: PgPool,
}

impl PgUserRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl UserRepository for PgUserRepository {
    async fn create(&self, user: &User) -> AppResult<User> {
        let result = sqlx::query_as::<_, User>(
            r#"
            INSERT INTO users (
                user_id, keycloak_id, email, username, first_name, last_name, phone,
                role, status, source, network_id, station_id, last_login_at,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            RETURNING *
            "#,
        )
        .bind(&user.user_id)
        .bind(&user.keycloak_id)
        .bind(&user.email)
        .bind(&user.username)
        .bind(&user.first_name)
        .bind(&user.last_name)
        .bind(&user.phone)
        .bind(&user.role)
        .bind(&user.status)
        .bind(&user.source)
        .bind(&user.network_id)
        .bind(&user.station_id)
        .bind(&user.last_login_at)
        .bind(&user.created_at)
        .bind(&user.updated_at)
        .fetch_one(&self.pool)
        .await?;

        Ok(result)
    }

    async fn find_by_id(&self, user_id: &str) -> AppResult<Option<User>> {
        let result = sqlx::query_as::<_, User>(
            "SELECT * FROM users WHERE user_id = $1 AND status != 'deleted'",
        )
        .bind(user_id)
        .fetch_optional(&self.pool)
        .await?;

        Ok(result)
    }

    async fn find_by_email(&self, email: &str) -> AppResult<Option<User>> {
        let result = sqlx::query_as::<_, User>(
            "SELECT * FROM users WHERE email = $1 AND status != 'deleted'",
        )
        .bind(email)
        .fetch_optional(&self.pool)
        .await?;

        Ok(result)
    }

    async fn find_by_keycloak_id(&self, keycloak_id: &str) -> AppResult<Option<User>> {
        let result = sqlx::query_as::<_, User>(
            "SELECT * FROM users WHERE keycloak_id = $1 AND status != 'deleted'",
        )
        .bind(keycloak_id)
        .fetch_optional(&self.pool)
        .await?;

        Ok(result)
    }

    async fn update(&self, user: &User) -> AppResult<User> {
        let result = sqlx::query_as::<_, User>(
            r#"
            UPDATE users SET
                email = $2,
                username = $3,
                first_name = $4,
                last_name = $5,
                phone = $6,
                role = $7,
                status = $8,
                network_id = $9,
                station_id = $10,
                last_login_at = $11,
                updated_at = $12
            WHERE user_id = $1
            RETURNING *
            "#,
        )
        .bind(&user.user_id)
        .bind(&user.email)
        .bind(&user.username)
        .bind(&user.first_name)
        .bind(&user.last_name)
        .bind(&user.phone)
        .bind(&user.role)
        .bind(&user.status)
        .bind(&user.network_id)
        .bind(&user.station_id)
        .bind(&user.last_login_at)
        .bind(Utc::now())
        .fetch_one(&self.pool)
        .await?;

        Ok(result)
    }

    async fn update_last_login(&self, user_id: &str) -> AppResult<()> {
        sqlx::query("UPDATE users SET last_login_at = $1, updated_at = $1 WHERE user_id = $2")
            .bind(Utc::now())
            .bind(user_id)
            .execute(&self.pool)
            .await?;

        Ok(())
    }

    async fn list_active(&self, limit: i64, offset: i64) -> AppResult<Vec<User>> {
        let results = sqlx::query_as::<_, User>(
            "SELECT * FROM users WHERE status != 'deleted' ORDER BY created_at DESC LIMIT $1 OFFSET $2"
        )
        .bind(limit)
        .bind(offset)
        .fetch_all(&self.pool)
        .await?;

        Ok(results)
    }

    async fn count_active(&self, network_id: Option<&str>) -> AppResult<i64> {
        let count: (i64,) = if let Some(net_id) = network_id {
            sqlx::query_as(
                "SELECT COUNT(*) FROM users WHERE status != 'deleted' AND network_id = $1",
            )
            .bind(net_id)
            .fetch_one(&self.pool)
            .await?
        } else {
            sqlx::query_as("SELECT COUNT(*) FROM users WHERE status != 'deleted'")
                .fetch_one(&self.pool)
                .await?
        };

        Ok(count.0)
    }
}
