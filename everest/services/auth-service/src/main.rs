use anyhow::Context;
use auth_service::core::{config::Config, logging};

#[actix_web::main]
async fn main() -> anyhow::Result<()> {
    let config = Config::from_env();
    logging::init_logging(&config.log_level);

    tracing::info!("Starting authentication service...");
    tracing::info!("Host: {}", config.host);
    tracing::info!("Port: {}", config.port);
    tracing::info!("Database: {}", mask_connection_string(&config.database_url));
    tracing::info!("Keycloak URL: {}", config.keycloak_url);
    tracing::info!("Keycloak Realm: {}", config.keycloak_realm);

    auth_service::run()
        .await
        .context("Application server crashed")?;

    Ok(())
}

fn mask_connection_string(conn_str: &str) -> String {
    if let Some(at_pos) = conn_str.find('@') {
        if let Some(slash_pos) = conn_str[..at_pos].rfind("//") {
            let prefix = &conn_str[..slash_pos + 2];
            let suffix = &conn_str[at_pos..];
            return format!("{}***:***{}", prefix, suffix);
        }
    }
    "***".to_string()
}
