use crate::application::dtos::network::{
    CreateNetworkRequest, NetworkResponse, UpdateNetworkRequest,
};
use crate::application::network_service::NetworkServiceImpl;
use crate::core::auth::{JwtValidator, require_admin_auth};
use crate::core::errors::AppError;
use crate::domain::services::NetworkService;
use crate::domain::value_objects::{CreateNetworkData, UpdateNetworkData};
use actix_web::{HttpRequest, HttpResponse, delete, get, post, put, web};
use std::sync::Arc;

#[utoipa::path(
    post,
    path = "/api/networks",
    tag = "Networks",
    request_body = CreateNetworkRequest,
    security(("bearer_auth" = [])),
    responses(
        (status = 201, description = "Network created", body = NetworkResponse),
        (status = 400, description = "Validation error"),
        (status = 401, description = "Unauthorized"),
        (status = 403, description = "Forbidden - Admin only")
    )
)]
#[post("/networks")]
pub async fn create_network(
    req: HttpRequest,
    body: web::Json<CreateNetworkRequest>,
    service: web::Data<Arc<NetworkServiceImpl>>,
    validator: web::Data<Arc<JwtValidator>>,
) -> Result<HttpResponse, AppError> {
    require_admin_auth(&req, &validator).await?;

    let network = service
        .create_network(CreateNetworkData {
            name: body.name.clone(),
            network_type: body.network_type.clone(),
            support_phone: body.support_phone.clone(),
            support_email: body.support_email.clone(),
        })
        .await?;

    Ok(HttpResponse::Created().json(NetworkResponse::from(network)))
}

#[utoipa::path(
    get,
    path = "/api/networks",
    tag = "Networks",
    params(
        ("limit" = Option<i64>, Query, description = "Items per page"),
        ("offset" = Option<i64>, Query, description = "Offset")
    ),
    responses(
        (status = 200, description = "Networks list", body = Vec<NetworkResponse>)
    )
)]
#[get("/networks")]
pub async fn list_networks(
    query: web::Query<ListQuery>,
    service: web::Data<Arc<NetworkServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let limit = query.limit.unwrap_or(50);
    let offset = query.offset.unwrap_or(0);

    let (networks, _total) = service.list_networks(limit, offset).await?;
    let response: Vec<NetworkResponse> = networks.into_iter().map(NetworkResponse::from).collect();

    Ok(HttpResponse::Ok().json(response))
}

#[derive(serde::Deserialize)]
pub struct ListQuery {
    pub limit: Option<i64>,
    pub offset: Option<i64>,
}

#[utoipa::path(
    get,
    path = "/api/networks/{id}",
    tag = "Networks",
    params(
        ("id" = String, Path, description = "Network ID")
    ),
    responses(
        (status = 200, description = "Network details", body = NetworkResponse),
        (status = 404, description = "Network not found")
    )
)]
#[get("/networks/{id}")]
pub async fn get_network(
    path: web::Path<String>,
    service: web::Data<Arc<NetworkServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let network = service.get_network(&path.into_inner()).await?;

    Ok(HttpResponse::Ok().json(NetworkResponse::from(network)))
}

#[utoipa::path(
    put,
    path = "/api/networks/{id}",
    tag = "Networks",
    params(
        ("id" = String, Path, description = "Network ID")
    ),
    request_body = UpdateNetworkRequest,
    security(("bearer_auth" = [])),
    responses(
        (status = 200, description = "Network updated", body = NetworkResponse),
        (status = 404, description = "Network not found"),
        (status = 401, description = "Unauthorized"),
        (status = 403, description = "Forbidden - Admin only")
    )
)]
#[put("/networks/{id}")]
pub async fn update_network(
    req: HttpRequest,
    path: web::Path<String>,
    body: web::Json<UpdateNetworkRequest>,
    service: web::Data<Arc<NetworkServiceImpl>>,
    validator: web::Data<Arc<JwtValidator>>,
) -> Result<HttpResponse, AppError> {
    require_admin_auth(&req, &validator).await?;

    let network = service
        .update_network(
            &path.into_inner(),
            UpdateNetworkData {
                name: body.name.clone(),
                network_type: body.network_type.clone(),
                support_phone: body.support_phone.clone(),
                support_email: body.support_email.clone(),
                is_verified: body.is_verified,
            },
        )
        .await?;

    Ok(HttpResponse::Ok().json(NetworkResponse::from(network)))
}

#[utoipa::path(
    delete,
    path = "/api/networks/{id}",
    tag = "Networks",
    params(
        ("id" = String, Path, description = "Network ID")
    ),
    security(("bearer_auth" = [])),
    responses(
        (status = 204, description = "Network deleted"),
        (status = 404, description = "Network not found"),
        (status = 401, description = "Unauthorized"),
        (status = 403, description = "Forbidden - Admin only")
    )
)]
#[delete("/networks/{id}")]
pub async fn delete_network(
    req: HttpRequest,
    path: web::Path<String>,
    service: web::Data<Arc<NetworkServiceImpl>>,
    validator: web::Data<Arc<JwtValidator>>,
) -> Result<HttpResponse, AppError> {
    require_admin_auth(&req, &validator).await?;

    service.delete_network(&path.into_inner()).await?;

    Ok(HttpResponse::NoContent().finish())
}

pub fn configure(cfg: &mut web::ServiceConfig) {
    cfg.service(create_network)
        .service(list_networks)
        .service(get_network)
        .service(update_network)
        .service(delete_network);
}
