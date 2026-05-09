use crate::application::connector_service::ConnectorServiceImpl;
use crate::application::dtos::connector::{
    ConnectorResponse, CreateConnectorRequest, UpdateConnectorRequest,
};
use crate::core::auth::{JwtValidator, require_admin_auth};
use crate::core::errors::AppError;
use crate::domain::services::ConnectorService;
use crate::domain::value_objects::{CreateConnectorData, UpdateConnectorData};
use actix_web::{HttpRequest, HttpResponse, delete, get, post, put, web};
use std::sync::Arc;

#[utoipa::path(
    post,
    path = "/api/connectors",
    tag = "Connectors",
    request_body = CreateConnectorRequest,
    security(("bearer_auth" = [])),
    responses(
        (status = 201, description = "Connector created", body = ConnectorResponse),
        (status = 400, description = "Validation error"),
        (status = 401, description = "Unauthorized"),
        (status = 403, description = "Forbidden - Admin only")
    )
)]
#[post("/connectors")]
pub async fn create_connector(
    req: HttpRequest,
    body: web::Json<CreateConnectorRequest>,
    service: web::Data<Arc<ConnectorServiceImpl>>,
    validator: web::Data<Arc<JwtValidator>>,
) -> Result<HttpResponse, AppError> {
    require_admin_auth(&req, &validator).await?;

    let connector = service
        .create_connector(CreateConnectorData {
            station_id: body.station_id.clone(),
            connector_type_id: body.connector_type_id,
            status_id: body.status_id,
            current_type_id: body.current_type_id,
            power_kw: body.power_kw, // No conversion needed
            voltage: body.voltage,
            amperage: body.amperage,
            count_available: body.count_available,
            count_total: body.count_total,
        })
        .await?;

    Ok(HttpResponse::Created().json(ConnectorResponse::from(connector)))
}

#[utoipa::path(
    get,
    path = "/api/connectors",
    tag = "Connectors",
    params(
        ("limit" = Option<i64>, Query, description = "Items per page"),
        ("offset" = Option<i64>, Query, description = "Offset"),
        ("station_id" = Option<String>, Query, description = "Filter by station ID")
    ),
    responses(
        (status = 200, description = "Connectors list", body = Vec<ConnectorResponse>)
    )
)]
#[get("/connectors")]
pub async fn list_connectors(
    query: web::Query<ConnectorListQuery>,
    service: web::Data<Arc<ConnectorServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let limit = query.limit.unwrap_or(50);
    let offset = query.offset.unwrap_or(0);

    let (connectors, _total) = service
        .list_connectors(query.station_id.clone(), limit, offset)
        .await?;
    let response: Vec<ConnectorResponse> = connectors
        .into_iter()
        .map(ConnectorResponse::from)
        .collect();

    Ok(HttpResponse::Ok().json(response))
}

#[derive(serde::Deserialize)]
pub struct ConnectorListQuery {
    pub limit: Option<i64>,
    pub offset: Option<i64>,
    pub station_id: Option<String>,
}

#[utoipa::path(
    get,
    path = "/api/connectors/{id}",
    tag = "Connectors",
    params(
        ("id" = String, Path, description = "Connector ID")
    ),
    responses(
        (status = 200, description = "Connector details", body = ConnectorResponse),
        (status = 404, description = "Connector not found")
    )
)]
#[get("/connectors/{id}")]
pub async fn get_connector(
    path: web::Path<String>,
    service: web::Data<Arc<ConnectorServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let connector = service.get_connector(&path.into_inner()).await?;

    Ok(HttpResponse::Ok().json(ConnectorResponse::from(connector)))
}

#[utoipa::path(
    put,
    path = "/api/connectors/{id}",
    tag = "Connectors",
    params(
        ("id" = String, Path, description = "Connector ID")
    ),
    request_body = UpdateConnectorRequest,
    security(("bearer_auth" = [])),
    responses(
        (status = 200, description = "Connector updated", body = ConnectorResponse),
        (status = 404, description = "Connector not found"),
        (status = 401, description = "Unauthorized"),
        (status = 403, description = "Forbidden - Admin only")
    )
)]
#[put("/connectors/{id}")]
pub async fn update_connector(
    req: HttpRequest,
    path: web::Path<String>,
    body: web::Json<UpdateConnectorRequest>,
    service: web::Data<Arc<ConnectorServiceImpl>>,
    validator: web::Data<Arc<JwtValidator>>,
) -> Result<HttpResponse, AppError> {
    require_admin_auth(&req, &validator).await?;

    let connector = service
        .update_connector(
            &path.into_inner(),
            UpdateConnectorData {
                connector_type_id: body.connector_type_id,
                status_id: body.status_id,
                current_type_id: body.current_type_id,
                power_kw: body.power_kw, // No conversion needed
                voltage: body.voltage,
                amperage: body.amperage,
                count_available: body.count_available,
                count_total: body.count_total,
            },
        )
        .await?;

    Ok(HttpResponse::Ok().json(ConnectorResponse::from(connector)))
}

#[utoipa::path(
    delete,
    path = "/api/connectors/{id}",
    tag = "Connectors",
    params(
        ("id" = String, Path, description = "Connector ID")
    ),
    security(("bearer_auth" = [])),
    responses(
        (status = 204, description = "Connector deleted"),
        (status = 404, description = "Connector not found"),
        (status = 401, description = "Unauthorized"),
        (status = 403, description = "Forbidden - Admin only")
    )
)]
#[delete("/connectors/{id}")]
pub async fn delete_connector(
    req: HttpRequest,
    path: web::Path<String>,
    service: web::Data<Arc<ConnectorServiceImpl>>,
    validator: web::Data<Arc<JwtValidator>>,
) -> Result<HttpResponse, AppError> {
    require_admin_auth(&req, &validator).await?;

    service.delete_connector(&path.into_inner()).await?;

    Ok(HttpResponse::NoContent().finish())
}

pub fn configure(cfg: &mut web::ServiceConfig) {
    cfg.service(create_connector)
        .service(list_connectors)
        .service(get_connector)
        .service(update_connector)
        .service(delete_connector);
}
