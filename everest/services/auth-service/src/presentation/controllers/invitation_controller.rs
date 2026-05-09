use crate::application::dtos::invitation::{
    AcceptInvitationRequest, CreateInvitationRequest, InvitationResponse, MessageResponse,
};
use crate::application::invitation_service::InvitationServiceImpl;
use crate::core::auth::{extract_bearer_token, validate_admin_role};
use crate::core::errors::AppError;
use crate::domain::services::InvitationService;
use actix_web::{delete, get, post, web, HttpRequest, HttpResponse};
use std::sync::Arc;

#[utoipa::path(
    post,
    path = "/api/invitations",
    tag = "Invitations",
    request_body = CreateInvitationRequest,
    security(
        ("bearer_auth" = [])
    ),
    responses(
        (status = 201, description = "Invitation created", body = InvitationResponse)
    )
)]
#[post("/invitations")]
pub async fn create_invitation(
    req: HttpRequest,
    body: web::Json<CreateInvitationRequest>,
    service: web::Data<Arc<InvitationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let token = extract_bearer_token(&req)?;
    let claims = validate_admin_role(&token).await?;
    let invited_by = claims.sub;

    let invitation = service
        .create_invitation(
            body.email.clone(),
            body.role.clone(),
            invited_by,
            body.expires_in_hours.unwrap_or(72),
            body.metadata.clone(),
        )
        .await?;

    Ok(HttpResponse::Created().json(InvitationResponse {
        code: invitation.code,
        expires_at: invitation.expires_at,
    }))
}

#[utoipa::path(
    get,
    path = "/api/invitations",
    tag = "Invitations",
    params(
        ("limit" = Option<i64>, Query, description = "Items per page"),
        ("offset" = Option<i64>, Query, description = "Offset")
    ),
    security(
        ("bearer_auth" = [])
    ),
    responses(
        (status = 200, description = "Invitations list", body = Vec<InvitationResponse>)
    )
)]
#[get("/invitations")]
pub async fn list_invitations(
    req: HttpRequest,
    query: web::Query<ListQuery>,
    service: web::Data<Arc<InvitationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let token = extract_bearer_token(&req)?;
    validate_admin_role(&token).await?;

    let limit = query.limit.unwrap_or(50);
    let offset = query.offset.unwrap_or(0);

    let invitations = service.list_invitations(limit, offset).await?;

    Ok(HttpResponse::Ok().json(invitations))
}

#[derive(serde::Deserialize)]
pub struct ListQuery {
    pub limit: Option<i64>,
    pub offset: Option<i64>,
}

#[utoipa::path(
    get,
    path = "/api/invitations/{code}",
    tag = "Invitations",
    params(
        ("code" = String, Path, description = "Invitation code")
    ),
    responses(
        (status = 200, description = "Invitation details", body = InvitationResponse),
        (status = 404, description = "Invalid code"),
        (status = 410, description = "Expired")
    )
)]
#[get("/invitations/{code}")]
pub async fn get_invitation(
    path: web::Path<String>,
    service: web::Data<Arc<InvitationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let invitation = service.get_invitation(path.into_inner()).await?;

    Ok(HttpResponse::Ok().json(invitation))
}

#[utoipa::path(
    post,
    path = "/api/invitations/{code}/accept",
    tag = "Invitations",
    params(
        ("code" = String, Path, description = "Invitation code")
    ),
    request_body = AcceptInvitationRequest,
    responses(
        (status = 200, description = "Invitation accepted", body = MessageResponse)
    )
)]
#[post("/invitations/{code}/accept")]
pub async fn accept_invitation(
    path: web::Path<String>,
    body: web::Json<AcceptInvitationRequest>,
    service: web::Data<Arc<InvitationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    service
        .accept_invitation(path.into_inner(), body.password.clone())
        .await?;

    Ok(HttpResponse::Ok().json(MessageResponse {
        message: "Invitation accepted. Account created.".to_string(),
    }))
}

#[utoipa::path(
    delete,
    path = "/api/invitations/{code}",
    tag = "Invitations",
    params(
        ("code" = String, Path, description = "Invitation code")
    ),
    security(
        ("bearer_auth" = [])
    ),
    responses(
        (status = 204, description = "Invitation cancelled")
    )
)]
#[delete("/invitations/{code}")]
pub async fn cancel_invitation(
    req: HttpRequest,
    path: web::Path<String>,
    service: web::Data<Arc<InvitationServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let token = extract_bearer_token(&req)?;
    validate_admin_role(&token).await?;

    service.cancel_invitation(path.into_inner()).await?;

    Ok(HttpResponse::NoContent().finish())
}

pub fn configure(cfg: &mut web::ServiceConfig) {
    cfg.service(create_invitation)
        .service(list_invitations)
        .service(get_invitation)
        .service(accept_invitation)
        .service(cancel_invitation);
}
