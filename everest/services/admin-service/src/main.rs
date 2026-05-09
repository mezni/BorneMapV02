use admin_service::core::{config::Config, logging};
use anyhow::Context;

#[actix_web::main]
async fn main() -> anyhow::Result<()> {
    let config = Config::from_env();
    logging::init_logging(&config.log_level);

    admin_service::run()
        .await
        .context("Application server crashed")?;

    Ok(())
}
