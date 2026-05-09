use crate::application::dtos::registration::{
    MessageResponse, RegisterRequest, RegisterResponse, ResendRequest, VerifyRequest,
};
use crate::application::registration_service::RegistrationServiceImpl;
use crate::core::errors::AppError;
use crate::domain::enums::Source;
use crate::domain::services::RegistrationService;
use actix_web::{post, web, HttpRequest, HttpResponse};
use std::sync::Arc;

#[utoipa::path(
    post,
    path = "/api/register",
    tag = "Registration",
    request_body = RegisterRequest,
    responses(
        (status = 201, description = "Registration created", body = RegisterResponse),
        (status = 409, description = "Email or username already exists"),
        (status = 400, description = "Validation error")
    )
)]
#[post("/register")]
pub async fn register(
    req: HttpRequest,
    body: web::Json<RegisterRequest>,
    service: web::Data<Arc<RegistrationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let ip_address = req
        .connection_info()
        .realip_remote_addr()
        .map(|s| s.to_string());

    let user_agent = req
        .headers()
        .get("user-agent")
        .and_then(|h| h.to_str().ok())
        .map(|s| s.to_string());

    let registration = service
        .register(
            body.email.clone(),
            body.username.clone(),
            body.password.clone(),
            body.first_name.clone(),
            body.last_name.clone(),
            body.phone.clone(),
            Source::Web,
            ip_address,
            user_agent,
        )
        .await?;

    Ok(HttpResponse::Created().json(RegisterResponse {
        message: "Registration created. Verification email sent.".to_string(),
    }))
}

#[utoipa::path(
    post,
    path = "/api/verify",
    tag = "Registration",
    request_body = VerifyRequest,
    responses(
        (status = 200, description = "Account verified", body = MessageResponse),
        (status = 410, description = "Verification expired"),
        (status = 400, description = "Invalid token")
    )
)]
#[post("/verify")]
pub async fn verify(
    body: web::Json<VerifyRequest>,
    service: web::Data<Arc<RegistrationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    service
        .verify(body.email.clone(), body.token.clone())
        .await?;

    Ok(HttpResponse::Ok().json(MessageResponse {
        message: "Account verified and activated.".to_string(),
    }))
}

#[utoipa::path(
    post,
    path = "/api/verify/resend",
    tag = "Registration",
    request_body = ResendRequest,
    responses(
        (status = 200, description = "Verification email resent", body = MessageResponse),
        (status = 429, description = "Resend limit exceeded"),
        (status = 404, description = "Registration not found")
    )
)]
#[post("/verify/resend")]
pub async fn resend_verification(
    body: web::Json<ResendRequest>,
    service: web::Data<Arc<RegistrationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    service.resend_verification(body.email.clone()).await?;

    Ok(HttpResponse::Ok().json(MessageResponse {
        message: "Verification email resent.".to_string(),
    }))
}

pub fn configure(cfg: &mut web::ServiceConfig) {
    cfg.service(register)
        .service(verify)
        .service(resend_verification);
}
