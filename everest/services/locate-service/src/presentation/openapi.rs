use crate::application::dtos::*;
use utoipa::{
    Modify, OpenApi,
    openapi::security::{HttpAuthScheme, HttpBuilder, SecurityScheme},
};
// Import the module so we can reference handlers
use crate::presentation::controllers;

#[derive(OpenApi)]
#[openapi(
    paths(
        controllers::get_nearby_stations,
        controllers::create_review,
        controllers::get_station_reviews,
        controllers::update_review,
        controllers::delete_review,
        controllers::get_user_info,
        controllers::health_check,
    ),
    components(
        schemas(
            NearbyStationsQuery,
            StationResponse,
            CreateReviewRequest,
            UpdateReviewRequest,
            ReviewResponse,
            // Ensure any nested structs within these DTOs are also added here
        )
    ),
    modifiers(&SecurityAddon),
    tags(
        (name = "stations", description = "Station management and discovery endpoints"),
        (name = "reviews", description = "User reviews and ratings operations"),
        (name = "user", description = "User profile and token information"),
        (name = "health", description = "Service health monitoring")
    )
)]
pub struct ApiDoc;

struct SecurityAddon;

impl Modify for SecurityAddon {
    fn modify(&self, openapi: &mut utoipa::openapi::OpenApi) {
        if let Some(components) = openapi.components.as_mut() {
            components.add_security_scheme(
                "bearer_auth",
                SecurityScheme::Http(
                    HttpBuilder::new()
                        .scheme(HttpAuthScheme::Bearer)
                        .bearer_format("JWT")
                        .build(),
                ),
            );
        }
    }
}
