use crate::application::dtos::health::HealthResponse;
use crate::application::health_service::HealthService;
use crate::core::errors::AppError;
use actix_web::{get, web, HttpResponse};
use std::sync::Arc;

#[utoipa::path(
    get,
    path = "/api/health",
    tag = "Health",
    responses(
        (status = 200, description = "Service health status", body = HealthResponse)
    )
)]
#[get("/health")]
pub async fn health_check(
    service: web::Data<Arc<HealthService>>,
) -> Result<HttpResponse, AppError> {
    let response = service.check_health().await?;
    Ok(HttpResponse::Ok().json(response))
}

pub fn configure(cfg: &mut web::ServiceConfig) {
    cfg.service(health_check);
}
