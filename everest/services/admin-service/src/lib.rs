pub mod application;
pub mod core;
pub mod domain;
pub mod infrastructure;
pub mod presentation;

use crate::application::connector_service::ConnectorServiceImpl;
use crate::application::health_service::HealthService;
use crate::application::network_service::NetworkServiceImpl;
use crate::application::station_service::StationServiceImpl;
use crate::core::auth::JwtValidator;
use crate::core::config::Config;
use crate::core::database::create_pool;
use crate::infrastructure::repositories::connector_repo::PgConnectorRepository;
use crate::infrastructure::repositories::network_repo::PgNetworkRepository;
use crate::infrastructure::repositories::station_repo::PgStationRepository;
use crate::presentation::openapi::ApiDoc;
use actix_cors::Cors;
use actix_web::{App, HttpServer, middleware, web};
use std::sync::Arc;
use utoipa::OpenApi;
use utoipa_swagger_ui::SwaggerUi;

pub async fn run() -> anyhow::Result<()> {
    let config = Config::from_env();
    tracing::info!("Starting admin service on {}", config.bind_address());

    // Database
    let db_pool = create_pool(&config.database_url).await?;
    tracing::info!("Database connected");

    // JWT Validator
    let jwt_validator = Arc::new(JwtValidator::new(
        config.jwks_url.clone(),
        config.jwt_issuer.clone(),
    ));
    tracing::info!("JWT validator initialized");

    // Repositories
    let network_repo = Arc::new(PgNetworkRepository::new(db_pool.clone()))
        as Arc<dyn crate::domain::repositories::NetworkRepository>;
    let station_repo = Arc::new(PgStationRepository::new(db_pool.clone()))
        as Arc<dyn crate::domain::repositories::StationRepository>;
    let connector_repo = Arc::new(PgConnectorRepository::new(db_pool.clone()))
        as Arc<dyn crate::domain::repositories::ConnectorRepository>;

    // Services
    let health_service = Arc::new(HealthService::new(db_pool.clone()));
    let network_service = Arc::new(NetworkServiceImpl::new(network_repo));
    let station_service = Arc::new(StationServiceImpl::new(station_repo));
    let connector_service = Arc::new(ConnectorServiceImpl::new(connector_repo));

    tracing::info!("Services initialized");

    // HTTP Server
    HttpServer::new(move || {
        let cors = Cors::default()
            .allow_any_origin()
            .allow_any_method()
            .allow_any_header()
            .max_age(3600);

        App::new()
            .wrap(cors)
            .wrap(middleware::Logger::default())
            .wrap(tracing_actix_web::TracingLogger::default())
            .app_data(web::Data::new(jwt_validator.clone()))
            .app_data(web::Data::new(health_service.clone()))
            .app_data(web::Data::new(network_service.clone()))
            .app_data(web::Data::new(station_service.clone()))
            .app_data(web::Data::new(connector_service.clone()))
            .configure(presentation::configure_routes)
            .service(
                SwaggerUi::new("/swagger-ui/{_:.*}")
                    .url("/api-docs/openapi.json", ApiDoc::openapi()),
            )
    })
    .bind(config.bind_address())?
    .run()
    .await?;

    Ok(())
}
