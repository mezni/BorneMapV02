use crate::core::errors::AppResult;
use crate::domain::entities::Connector;
use crate::domain::repositories::ConnectorRepository;
use async_trait::async_trait;
use chrono::Utc;
use sqlx::PgPool;

pub struct PgConnectorRepository {
    pool: PgPool,
}

impl PgConnectorRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl ConnectorRepository for PgConnectorRepository {
    async fn create(&self, connector: &Connector) -> AppResult<Connector> {
        let result = sqlx::query_as::<_, Connector>(
            r#"
            INSERT INTO connectors (
                connector_id, station_id, connector_type_id, status_id, current_type_id,
                power_kw, voltage, amperage, count_available, count_total,
                created_by, created_at, updated_by, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING *
            "#,
        )
        .bind(&connector.connector_id)
        .bind(&connector.station_id)
        .bind(connector.connector_type_id)
        .bind(connector.status_id)
        .bind(connector.current_type_id)
        .bind(&connector.power_kw)
        .bind(connector.voltage)
        .bind(connector.amperage)
        .bind(connector.count_available)
        .bind(connector.count_total)
        .bind(&connector.created_by)
        .bind(&connector.created_at)
        .bind(&connector.updated_by)
        .bind(&connector.updated_at)
        .fetch_one(&self.pool)
        .await?;

        Ok(result)
    }

    async fn find_by_id(&self, connector_id: &str) -> AppResult<Option<Connector>> {
        let result =
            sqlx::query_as::<_, Connector>("SELECT * FROM connectors WHERE connector_id = $1")
                .bind(connector_id)
                .fetch_optional(&self.pool)
                .await?;

        Ok(result)
    }

    async fn find_by_station(&self, station_id: &str) -> AppResult<Vec<Connector>> {
        let results = sqlx::query_as::<_, Connector>(
            "SELECT * FROM connectors WHERE station_id = $1 ORDER BY created_at DESC",
        )
        .bind(station_id)
        .fetch_all(&self.pool)
        .await?;

        Ok(results)
    }

    async fn find_all(&self, limit: i64, offset: i64) -> AppResult<Vec<Connector>> {
        let results = sqlx::query_as::<_, Connector>(
            "SELECT * FROM connectors ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        )
        .bind(limit)
        .bind(offset)
        .fetch_all(&self.pool)
        .await?;

        Ok(results)
    }

    async fn update(&self, connector: &Connector) -> AppResult<Connector> {
        let result = sqlx::query_as::<_, Connector>(
            r#"
            UPDATE connectors SET
                connector_type_id = $2,
                status_id = $3,
                current_type_id = $4,
                power_kw = $5,
                voltage = $6,
                amperage = $7,
                count_available = $8,
                count_total = $9,
                updated_by = $10,
                updated_at = $11
            WHERE connector_id = $1
            RETURNING *
            "#,
        )
        .bind(&connector.connector_id)
        .bind(connector.connector_type_id)
        .bind(connector.status_id)
        .bind(connector.current_type_id)
        .bind(&connector.power_kw)
        .bind(connector.voltage)
        .bind(connector.amperage)
        .bind(connector.count_available)
        .bind(connector.count_total)
        .bind(&connector.updated_by)
        .bind(Utc::now())
        .fetch_one(&self.pool)
        .await?;

        Ok(result)
    }

    async fn delete(&self, connector_id: &str) -> AppResult<()> {
        sqlx::query("DELETE FROM connectors WHERE connector_id = $1")
            .bind(connector_id)
            .execute(&self.pool)
            .await?;

        Ok(())
    }

    async fn count(&self) -> AppResult<i64> {
        let count: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM connectors")
            .fetch_one(&self.pool)
            .await?;

        Ok(count.0)
    }
}
