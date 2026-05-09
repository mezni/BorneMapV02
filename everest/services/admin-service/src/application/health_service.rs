use crate::application::dtos::health::HealthResponse;
use crate::core::database::check_database_health;
use crate::core::errors::AppResult;
use chrono::Utc;
use sqlx::PgPool;
use std::sync::Arc;

pub struct HealthService {
    db_pool: PgPool,
}

impl HealthService {
    pub fn new(db_pool: PgPool) -> Self {
        Self { db_pool }
    }

    pub async fn check_health(&self) -> AppResult<HealthResponse> {
        let db_status = if check_database_health(&self.db_pool).await {
            "up"
        } else {
            "down"
        };

        Ok(HealthResponse {
            status: if db_status == "up" {
                "ok".to_string()
            } else {
                "degraded".to_string()
            },
            db: db_status.to_string(),
            timestamp: Utc::now().to_rfc3339(),
        })
    }
}
