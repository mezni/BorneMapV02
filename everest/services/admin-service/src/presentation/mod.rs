pub mod controllers;
pub mod openapi;

use actix_web::web;

pub fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("/api")
            .configure(controllers::health_controller::configure)
            .configure(controllers::network_controller::configure)
            .configure(controllers::station_controller::configure)
            .configure(controllers::connector_controller::configure),
    );
}
