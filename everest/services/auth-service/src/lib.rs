pub mod application;
pub mod core;
pub mod domain;
pub mod infrastructure;
pub mod presentation;

use crate::application::admin_service::AdminServiceImpl;
use crate::application::authentication_service::AuthenticationServiceImpl;
use crate::application::health_service::HealthService;
use crate::application::invitation_service::InvitationServiceImpl;
use crate::application::registration_service::RegistrationServiceImpl;
use crate::core::config::Config;
use crate::core::database::create_pool;
use crate::infrastructure::keycloak_client::HttpKeycloakClient;
use crate::infrastructure::repositories::invitation_repo::PgInvitationRepository;
use crate::infrastructure::repositories::registration_repo::PgRegistrationRepository;
use crate::infrastructure::repositories::user_repo::PgUserRepository;
use crate::presentation::openapi::ApiDoc;
use actix_cors::Cors;
use actix_web::{middleware, web, App, HttpServer};
use std::sync::Arc;
use utoipa::OpenApi;
use utoipa_swagger_ui::SwaggerUi;

pub async fn run() -> anyhow::Result<()> {
    let config = Config::from_env();
    tracing::info!("Starting auth service on {}", config.bind_address());

    // Database
    let db_pool = create_pool(&config.database_url).await?;
    tracing::info!("Database connected");

    // Keycloak client
    let keycloak = Arc::new(HttpKeycloakClient::new(
        config.keycloak_url.clone(),
        config.keycloak_realm.clone(),
        config.keycloak_backend_client_id.clone(),
        config.keycloak_backend_client_secret.clone(),
        config.keycloak_auth_client_id.clone(),
    )) as Arc<dyn crate::infrastructure::keycloak_client::KeycloakClient>;
    tracing::info!("Keycloak client initialized");

    // Repositories
    let user_repo = Arc::new(PgUserRepository::new(db_pool.clone()))
        as Arc<dyn crate::domain::repositories::UserRepository>;
    let registration_repo = Arc::new(PgRegistrationRepository::new(db_pool.clone()))
        as Arc<dyn crate::domain::repositories::RegistrationRepository>;
    let invitation_repo = Arc::new(PgInvitationRepository::new(db_pool.clone()))
        as Arc<dyn crate::domain::repositories::InvitationRepository>;

    // Services
    let health_service = Arc::new(HealthService::new(db_pool.clone(), keycloak.clone()));
    let registration_service = Arc::new(RegistrationServiceImpl::new(
        user_repo.clone(),
        registration_repo.clone(),
        keycloak.clone(),
    ));
    let auth_service = Arc::new(AuthenticationServiceImpl::new(
        user_repo.clone(),
        keycloak.clone(),
    ));
    let admin_service = Arc::new(AdminServiceImpl::new(user_repo.clone(), keycloak.clone()));
    let invitation_service = Arc::new(InvitationServiceImpl::new(
        invitation_repo.clone(),
        user_repo.clone(),
        keycloak.clone(),
    ));

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
            .app_data(web::Data::new(health_service.clone()))
            .app_data(web::Data::new(registration_service.clone()))
            .app_data(web::Data::new(auth_service.clone()))
            .app_data(web::Data::new(admin_service.clone()))
            .app_data(web::Data::new(invitation_service.clone()))
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
