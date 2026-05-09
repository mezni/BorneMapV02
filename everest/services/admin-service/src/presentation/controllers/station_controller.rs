use crate::application::dtos::station::{
    CreateStationRequest, StationResponse, UpdateStationRequest,
};
use crate::application::station_service::StationServiceImpl;
use crate::core::auth::{JwtValidator, require_admin_auth};
use crate::core::errors::AppError;
use crate::domain::services::StationService;
use crate::domain::value_objects::{CreateStationData, UpdateStationData};
use actix_web::{HttpRequest, HttpResponse, delete, get, post, put, web};
use std::sync::Arc;

#[utoipa::path(
    post,
    path = "/api/stations",
    tag = "Stations",
    request_body = CreateStationRequest,
    security(("bearer_auth" = [])),
    responses(
        (status = 201, description = "Station created", body = StationResponse),
        (status = 400, description = "Validation error"),
        (status = 401, description = "Unauthorized"),
        (status = 403, description = "Forbidden - Admin only")
    )
)]
#[post("/stations")]
pub async fn create_station(
    req: HttpRequest,
    body: web::Json<CreateStationRequest>,
    service: web::Data<Arc<StationServiceImpl>>,
    validator: web::Data<Arc<JwtValidator>>,
) -> Result<HttpResponse, AppError> {
    require_admin_auth(&req, &validator).await?;

    let station = service
        .create_station(CreateStationData {
            osm_id: body.osm_id,
            name: body.name.clone(),
            address: body.address.clone(),
            latitude: body.latitude,
            longitude: body.longitude,
            tags: body
                .tags
                .as_ref()
                .map(|t| serde_json::to_value(t).unwrap_or_default()),
            network_id: body.network_id.clone(),
        })
        .await?;

    Ok(HttpResponse::Created().json(StationResponse::from(station)))
}

#[utoipa::path(
    get,
    path = "/api/stations",
    tag = "Stations",
    params(
        ("limit" = Option<i64>, Query, description = "Items per page"),
        ("offset" = Option<i64>, Query, description = "Offset"),
        ("network_id" = Option<String>, Query, description = "Filter by network ID")
    ),
    responses(
        (status = 200, description = "Stations list", body = Vec<StationResponse>)
    )
)]
#[get("/stations")]
pub async fn list_stations(
    query: web::Query<StationListQuery>,
    service: web::Data<Arc<StationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let limit = query.limit.unwrap_or(50);
    let offset = query.offset.unwrap_or(0);

    let (stations, _total) = service
        .list_stations(query.network_id.clone(), limit, offset)
        .await?;
    let response: Vec<StationResponse> = stations.into_iter().map(StationResponse::from).collect();

    Ok(HttpResponse::Ok().json(response))
}

#[derive(serde::Deserialize)]
pub struct StationListQuery {
    pub limit: Option<i64>,
    pub offset: Option<i64>,
    pub network_id: Option<String>,
}

#[utoipa::path(
    get,
    path = "/api/stations/{id}",
    tag = "Stations",
    params(
        ("id" = String, Path, description = "Station ID")
    ),
    responses(
        (status = 200, description = "Station details", body = StationResponse),
        (status = 404, description = "Station not found")
    )
)]
#[get("/stations/{id}")]
pub async fn get_station(
    path: web::Path<String>,
    service: web::Data<Arc<StationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let station = service.get_station(&path.into_inner()).await?;

    Ok(HttpResponse::Ok().json(StationResponse::from(station)))
}

#[utoipa::path(
    put,
    path = "/api/stations/{id}",
    tag = "Stations",
    params(
        ("id" = String, Path, description = "Station ID")
    ),
    request_body = UpdateStationRequest,
    security(("bearer_auth" = [])),
    responses(
        (status = 200, description = "Station updated", body = StationResponse),
        (status = 404, description = "Station not found"),
        (status = 401, description = "Unauthorized"),
        (status = 403, description = "Forbidden - Admin only")
    )
)]
#[put("/stations/{id}")]
pub async fn update_station(
    req: HttpRequest,
    path: web::Path<String>,
    body: web::Json<UpdateStationRequest>,
    service: web::Data<Arc<StationServiceImpl>>,
    validator: web::Data<Arc<JwtValidator>>,
) -> Result<HttpResponse, AppError> {
    require_admin_auth(&req, &validator).await?;

    let station = service
        .update_station(
            &path.into_inner(),
            UpdateStationData {
                name: body.name.clone(),
                address: body.address.clone(),
                latitude: body.latitude,
                longitude: body.longitude,
                tags: body
                    .tags
                    .as_ref()
                    .map(|t| serde_json::to_value(t).unwrap_or_default()),
                network_id: body.network_id.clone(),
            },
        )
        .await?;

    Ok(HttpResponse::Ok().json(StationResponse::from(station)))
}

#[utoipa::path(
    delete,
    path = "/api/stations/{id}",
    tag = "Stations",
    params(
        ("id" = String, Path, description = "Station ID")
    ),
    security(("bearer_auth" = [])),
    responses(
        (status = 204, description = "Station deleted"),
        (status = 404, description = "Station not found"),
        (status = 401, description = "Unauthorized"),
        (status = 403, description = "Forbidden - Admin only")
    )
)]
#[delete("/stations/{id}")]
pub async fn delete_station(
    req: HttpRequest,
    path: web::Path<String>,
    service: web::Data<Arc<StationServiceImpl>>,
    validator: web::Data<Arc<JwtValidator>>,
) -> Result<HttpResponse, AppError> {
    require_admin_auth(&req, &validator).await?;

    service.delete_station(&path.into_inner()).await?;

    Ok(HttpResponse::NoContent().finish())
}

pub fn configure(cfg: &mut web::ServiceConfig) {
    cfg.service(create_station)
        .service(list_stations)
        .service(get_station)
        .service(update_station)
        .service(delete_station);
}
