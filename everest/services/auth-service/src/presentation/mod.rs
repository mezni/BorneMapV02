pub mod controllers;
pub mod openapi;

use actix_web::web;

pub fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("/api")
            .configure(controllers::health_controller::configure)
            .configure(controllers::registration_controller::configure)
            .configure(controllers::authentication_controller::configure)
            .configure(controllers::admin_controller::configure)
            .configure(controllers::invitation_controller::configure),
    );
}
