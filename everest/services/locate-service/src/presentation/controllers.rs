use crate::application::dtos::*;
use crate::application::review_service::ReviewServiceImpl;
use crate::application::station_service::StationServiceImpl;
use crate::core::auth::{JwtValidator, TokenClaims, extract_bearer_token};
use crate::core::errors::{AppError, AppResult};
use crate::domain::services::{ReviewService, StationService};
use actix_web::{HttpRequest, HttpResponse, web};

#[utoipa::path(
    get,
    path = "/api/stations/nearby",
    params(
        ("latitude" = f64, Query, description = "Latitude coordinate"),
        ("longitude" = f64, Query, description = "Longitude coordinate"),
        ("radius_meters" = Option<i32>, Query, description = "Search radius in meters (default: 20000)"),
        ("limit" = Option<i32>, Query, description = "Maximum number of results (default: 5)")
    ),
    responses(
        (status = 200, description = "List of nearby stations", body = Vec<StationResponse>),
        (status = 500, description = "Internal server error")
    ),
    tag = "stations"
)]
pub async fn get_nearby_stations(
    query: web::Query<NearbyStationsQuery>,
    station_service: web::Data<StationServiceImpl>,
) -> AppResult<HttpResponse> {
    let stations = station_service
        .find_nearby_stations(
            query.latitude,
            query.longitude,
            query.radius_meters,
            query.limit,
        )
        .await?;

    let response: Vec<StationResponse> = stations.into_iter().map(StationResponse::from).collect();

    Ok(HttpResponse::Ok().json(response))
}

#[utoipa::path(
    post,
    path = "/api/reviews",
    request_body = CreateReviewRequest,
    responses(
        (status = 201, description = "Review created successfully", body = ReviewResponse),
        (status = 400, description = "Invalid request"),
        (status = 401, description = "Unauthorized"),
        (status = 403, description = "Forbidden - user role required"),
        (status = 500, description = "Internal server error")
    ),
    security(("bearer_auth" = [])),
    tag = "reviews"
)]
pub async fn create_review(
    req: HttpRequest,
    payload: web::Json<CreateReviewRequest>,
    review_service: web::Data<ReviewServiceImpl>,
    validator: web::Data<JwtValidator>,
) -> AppResult<HttpResponse> {
    let token = extract_bearer_token(&req)?;
    let claims = validator.validate_user_role(&token).await?;

    let user_id = claims.sub.clone();

    let review = review_service
        .create_review(
            user_id.clone(),
            payload.station_id.clone(),
            payload.rating,
            payload.review_text.clone(),
            user_id,
        )
        .await?;

    Ok(HttpResponse::Created().json(ReviewResponse::from(review)))
}

#[utoipa::path(
    get,
    path = "/api/reviews/station/{station_id}",
    params(
        ("station_id" = String, Path, description = "Station ID")
    ),
    responses(
        (status = 200, description = "List of reviews for the station", body = Vec<ReviewResponse>),
        (status = 401, description = "Unauthorized"),
        (status = 500, description = "Internal server error")
    ),
    security(("bearer_auth" = [])),
    tag = "reviews"
)]
pub async fn get_station_reviews(
    req: HttpRequest,
    station_id: web::Path<String>,
    review_service: web::Data<ReviewServiceImpl>,
    validator: web::Data<JwtValidator>,
) -> AppResult<HttpResponse> {
    let token = extract_bearer_token(&req)?;
    let _ = validator.validate_user_role(&token).await?;

    let reviews = review_service.get_reviews_by_station(&station_id).await?;
    let response: Vec<ReviewResponse> = reviews.into_iter().map(ReviewResponse::from).collect();

    Ok(HttpResponse::Ok().json(response))
}

#[utoipa::path(
    put,
    path = "/api/reviews/{review_id}",
    params(
        ("review_id" = String, Path, description = "Review ID")
    ),
    request_body = UpdateReviewRequest,
    responses(
        (status = 200, description = "Review updated successfully", body = ReviewResponse),
        (status = 400, description = "Invalid request"),
        (status = 401, description = "Unauthorized"),
        (status = 404, description = "Review not found"),
        (status = 500, description = "Internal server error")
    ),
    security(("bearer_auth" = [])),
    tag = "reviews"
)]
pub async fn update_review(
    req: HttpRequest,
    review_id: web::Path<String>,
    payload: web::Json<UpdateReviewRequest>,
    review_service: web::Data<ReviewServiceImpl>,
    validator: web::Data<JwtValidator>,
) -> AppResult<HttpResponse> {
    let token = extract_bearer_token(&req)?;
    let claims = validator.validate_user_role(&token).await?;

    let updated_by = claims.sub.clone();

    let review = review_service
        .update_review(
            &review_id,
            payload.rating,
            payload.review_text.clone(),
            updated_by,
        )
        .await?;

    Ok(HttpResponse::Ok().json(ReviewResponse::from(review)))
}

#[utoipa::path(
    delete,
    path = "/api/reviews/{review_id}",
    params(
        ("review_id" = String, Path, description = "Review ID")
    ),
    responses(
        (status = 204, description = "Review deleted successfully"),
        (status = 401, description = "Unauthorized"),
        (status = 404, description = "Review not found"),
        (status = 500, description = "Internal server error")
    ),
    security(("bearer_auth" = [])),
    tag = "reviews"
)]
pub async fn delete_review(
    req: HttpRequest,
    review_id: web::Path<String>,
    review_service: web::Data<ReviewServiceImpl>,
    validator: web::Data<JwtValidator>,
) -> AppResult<HttpResponse> {
    let token = extract_bearer_token(&req)?;
    let _ = validator.validate_user_role(&token).await?;

    review_service.delete_review(&review_id).await?;

    Ok(HttpResponse::NoContent().finish())
}

#[utoipa::path(
    get,
    path = "/health",
    responses(
        (status = 200, description = "Service is healthy")
    ),
    tag = "health"
)]
pub async fn health_check() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({
        "status": "healthy",
        "service": "locate-service"
    }))
}

#[utoipa::path(
    get,
    path = "/api/user/info",
    responses(
        (status = 200, description = "User information from token"),
        (status = 401, description = "Unauthorized")
    ),
    security(("bearer_auth" = [])),
    tag = "user"
)]
pub async fn get_user_info(
    req: HttpRequest,
    validator: web::Data<JwtValidator>,
) -> AppResult<HttpResponse> {
    let token = extract_bearer_token(&req)?;
    let claims = validator.validate_token(&token).await?;

    Ok(HttpResponse::Ok().json(serde_json::json!({
        "user_id": claims.sub,
        "jti": claims.jti,
        "roles": claims.get_roles(),
        "network_id": claims.network_id,
        "station_id": claims.station_id,
        "email": claims.email,
        "username": claims.preferred_username,
    })))
}
