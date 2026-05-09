use crate::core::errors::AppResult;
use crate::domain::entities::Network;
use crate::domain::repositories::NetworkRepository;
use async_trait::async_trait;
use chrono::Utc;
use sqlx::PgPool;

pub struct PgNetworkRepository {
    pool: PgPool,
}

impl PgNetworkRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl NetworkRepository for PgNetworkRepository {
    async fn create(&self, network: &Network) -> AppResult<Network> {
        let result = sqlx::query_as::<_, Network>(
            r#"
            INSERT INTO networks (
                network_id, name, network_type, support_phone, support_email,
                is_verified, created_at, updated_at, created_by, updated_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
            "#,
        )
        .bind(&network.network_id)
        .bind(&network.name)
        .bind(&network.network_type)
        .bind(&network.support_phone)
        .bind(&network.support_email)
        .bind(&network.is_verified)
        .bind(&network.created_at)
        .bind(&network.updated_at)
        .bind(&network.created_by)
        .bind(&network.updated_by)
        .fetch_one(&self.pool)
        .await?;

        Ok(result)
    }

    async fn find_by_id(&self, network_id: &str) -> AppResult<Option<Network>> {
        let result = sqlx::query_as::<_, Network>("SELECT * FROM networks WHERE network_id = $1")
            .bind(network_id)
            .fetch_optional(&self.pool)
            .await?;

        Ok(result)
    }

    async fn find_all(&self, limit: i64, offset: i64) -> AppResult<Vec<Network>> {
        let results = sqlx::query_as::<_, Network>(
            "SELECT * FROM networks ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        )
        .bind(limit)
        .bind(offset)
        .fetch_all(&self.pool)
        .await?;

        Ok(results)
    }

    async fn update(&self, network: &Network) -> AppResult<Network> {
        let result = sqlx::query_as::<_, Network>(
            r#"
            UPDATE networks SET
                name = $2,
                network_type = $3,
                support_phone = $4,
                support_email = $5,
                is_verified = $6,
                updated_at = $7,
                updated_by = $8
            WHERE network_id = $1
            RETURNING *
            "#,
        )
        .bind(&network.network_id)
        .bind(&network.name)
        .bind(&network.network_type)
        .bind(&network.support_phone)
        .bind(&network.support_email)
        .bind(&network.is_verified)
        .bind(Utc::now())
        .bind(&network.updated_by)
        .fetch_one(&self.pool)
        .await?;

        Ok(result)
    }

    async fn delete(&self, network_id: &str) -> AppResult<()> {
        sqlx::query("DELETE FROM networks WHERE network_id = $1")
            .bind(network_id)
            .execute(&self.pool)
            .await?;

        Ok(())
    }

    async fn count(&self) -> AppResult<i64> {
        let count: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM networks")
            .fetch_one(&self.pool)
            .await?;

        Ok(count.0)
    }
}
