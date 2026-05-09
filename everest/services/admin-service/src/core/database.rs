use sqlx::{PgPool, postgres::PgPoolOptions};
use std::time::Duration;

pub async fn create_pool(database_url: &str) -> Result<PgPool, anyhow::Error> {
    // 1. Assign the result of the connection to the 'pool' variable
    let pool = PgPoolOptions::new()
        .max_connections(10)
        .acquire_timeout(Duration::from_secs(5))
        .connect(database_url)
        .await
        .map_err(|e| anyhow::anyhow!("Failed to connect to DB: {}", e))?;

    // 2. Now 'pool' exists and can be passed here
    run_migrations(&pool).await?;

    Ok(pool)
}

pub async fn check_database_health(pool: &PgPool) -> bool {
    sqlx::query("SELECT 1").fetch_one(pool).await.is_ok()
}

pub async fn run_migrations(pool: &PgPool) -> anyhow::Result<()> {
    tracing::info!("Running database migrations...");

    // This looks for the /migrations folder relative to the project root
    sqlx::migrate!("./migrations")
        .run(pool)
        .await
        .map_err(|e| anyhow::anyhow!("Migration failed: {}", e))?;

    tracing::info!("Migrations completed successfully");
    Ok(())
}
