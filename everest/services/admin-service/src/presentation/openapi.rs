use utoipa::Modify;
use utoipa::OpenApi;
use utoipa::openapi::security::{HttpAuthScheme, HttpBuilder, SecurityScheme};

#[derive(OpenApi)]
#[openapi(
    paths(
        crate::presentation::controllers::health_controller::health_check,
        crate::presentation::controllers::network_controller::list_networks,
        crate::presentation::controllers::network_controller::get_network,
        crate::presentation::controllers::network_controller::create_network,
        crate::presentation::controllers::network_controller::update_network,
        crate::presentation::controllers::network_controller::delete_network,
        crate::presentation::controllers::station_controller::list_stations,
        crate::presentation::controllers::station_controller::get_station,
        crate::presentation::controllers::station_controller::create_station,
        crate::presentation::controllers::station_controller::update_station,
        crate::presentation::controllers::station_controller::delete_station,
        crate::presentation::controllers::connector_controller::list_connectors,
        crate::presentation::controllers::connector_controller::get_connector,
        crate::presentation::controllers::connector_controller::create_connector,
        crate::presentation::controllers::connector_controller::update_connector,
        crate::presentation::controllers::connector_controller::delete_connector,
    ),
    components(schemas(
                crate::application::dtos::health::HealthResponse,
        crate::application::dtos::network::CreateNetworkRequest,
        crate::application::dtos::network::UpdateNetworkRequest,
        crate::application::dtos::network::NetworkResponse,
        crate::application::dtos::station::CreateStationRequest,
        crate::application::dtos::station::UpdateStationRequest,
        crate::application::dtos::station::StationResponse,
        crate::application::dtos::connector::CreateConnectorRequest,
        crate::application::dtos::connector::UpdateConnectorRequest,
        crate::application::dtos::connector::ConnectorResponse,
    )),
    modifiers(&SecurityAddon),
    tags(
        (name = "Health", description = "Health check endpoints"),
        (name = "Networks", description = "Networks endpoints"),
        (name = "Stations", description = "Stations endpoints"),
        (name = "Connectors", description = "Connectors endpoints"),
    ),
    info(
        title = "Admin Service API",
        version = "1.0.0",
        description = "Admin management service"
    )
)]
pub struct ApiDoc;

struct SecurityAddon;

impl Modify for SecurityAddon {
    fn modify(&self, openapi: &mut utoipa::openapi::OpenApi) {
        let components = openapi.components.as_mut().unwrap();

        components.add_security_scheme(
            "bearer_auth",
            SecurityScheme::Http(
                HttpBuilder::new()
                    .scheme(HttpAuthScheme::Bearer)
                    .bearer_format("JWT")
                    .description(Some("Enter your Keycloak JWT token".to_string()))
                    .build(),
            ),
        );
    }
}
