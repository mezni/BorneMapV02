pub mod controllers;
pub mod openapi;

use actix_web::web;

pub fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("/api")
            .service(
                web::scope("/stations")
                    .route("/nearby", web::get().to(controllers::get_nearby_stations)),
            )
            .service(
                web::scope("/reviews")
                    .route("", web::post().to(controllers::create_review))
                    .route(
                        "/station/{station_id}",
                        web::get().to(controllers::get_station_reviews),
                    )
                    .route("/{review_id}", web::put().to(controllers::update_review))
                    .route("/{review_id}", web::delete().to(controllers::delete_review)),
            )
            .service(web::scope("/user").route("/info", web::get().to(controllers::get_user_info))),
    )
    .route("/health", web::get().to(controllers::health_check));
}
