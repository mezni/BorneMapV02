use crate::application::authentication_service::AuthenticationServiceImpl;
use crate::application::dtos::authentication::{
    LoginRequest, LoginResponse, LogoutRequest, RefreshRequest, ValidateRequest, ValidateResponse,
};
use crate::core::auth::extract_bearer_token;
use crate::core::errors::AppError;
use crate::domain::services::AuthenticationService;
use actix_web::HttpRequest;
use actix_web::{post, web, HttpResponse};
use std::sync::Arc;

#[utoipa::path(
    post,
    path = "/api/auth/login",
    tag = "Authentication",
    request_body = LoginRequest,
    responses(
        (status = 200, description = "Login successful", body = LoginResponse),
        (status = 401, description = "Invalid credentials"),
        (status = 403, description = "Account not verified or disabled")
    )
)]
#[post("/auth/login")]
pub async fn login(
    body: web::Json<LoginRequest>,
    service: web::Data<Arc<AuthenticationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let response = service
        .login(body.username.clone(), body.password.clone())
        .await?;

    Ok(HttpResponse::Ok().json(response))
}

#[utoipa::path(
    post,
    path = "/api/auth/logout",
    tag = "Authentication",
    request_body = LogoutRequest,
    security(
        ("bearer_auth" = [])
    ),
    responses(
        (status = 204, description = "Logout successful")
    )
)]
#[post("/auth/logout")]
pub async fn logout(
    req: HttpRequest,
    body: web::Json<LogoutRequest>,
    service: web::Data<Arc<AuthenticationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    // Validate bearer token
    extract_bearer_token(&req)?;

    service.logout(body.refresh_token.clone()).await?;

    Ok(HttpResponse::NoContent().finish())
}

#[utoipa::path(
    post,
    path = "/api/auth/refresh",
    tag = "Authentication",
    request_body = RefreshRequest,
    responses(
        (status = 200, description = "Token refreshed", body = LoginResponse),
        (status = 401, description = "Invalid or expired refresh token")
    )
)]
#[post("/auth/refresh")]
pub async fn refresh_token(
    body: web::Json<RefreshRequest>,
    service: web::Data<Arc<AuthenticationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let response = service.refresh_token(body.refresh_token.clone()).await?;

    Ok(HttpResponse::Ok().json(response))
}

#[utoipa::path(
    post,
    path = "/api/auth/validate",
    tag = "Authentication",
    request_body = ValidateRequest,
    responses(
        (status = 200, description = "Token is valid", body = ValidateResponse),
        (status = 401, description = "Invalid or inactive token")
    )
)]
#[post("/auth/validate")]
pub async fn validate_token(
    body: web::Json<ValidateRequest>,
    service: web::Data<Arc<AuthenticationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let token_info = service.validate_token(body.access_token.clone()).await?;

    Ok(HttpResponse::Ok().json(token_info))
}

pub fn configure(cfg: &mut web::ServiceConfig) {
    cfg.service(login)
        .service(logout)
        .service(refresh_token)
        .service(validate_token);
}
