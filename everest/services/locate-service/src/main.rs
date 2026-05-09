// =============================================================================
// src/main.rs
// =============================================================================
use anyhow::Context;
use locate_service::core::{config::Config, logging};

#[actix_web::main]
async fn main() -> anyhow::Result<()> {
    let config = Config::from_env();
    logging::init_logging(&config.log_level);

    locate_service::run()
        .await
        .context("Application server crashed")?;

    Ok(())
}
