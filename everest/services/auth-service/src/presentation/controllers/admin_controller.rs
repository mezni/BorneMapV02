use crate::application::admin_service::AdminServiceImpl;
use crate::application::dtos::admin::{
    CreateUserRequest, MessageResponse, UpdateUserRequest, UserResponse,
};
use crate::core::auth::{extract_bearer_token, validate_admin_role};
use crate::core::errors::AppError;
use crate::domain::services::AdminService;
use crate::domain::value_objects::{CreateUserData, UpdateUserData};
use actix_web::{delete, get, post, put, web, HttpRequest, HttpResponse};
use std::sync::Arc;

#[utoipa::path(
    get,
    path = "/api/admin/users",
    tag = "Admin",
    params(
        ("limit" = Option<i64>, Query, description = "Items per page"),
        ("offset" = Option<i64>, Query, description = "Offset")
    ),
    security(
        ("bearer_auth" = [])
    ),
    responses(
        (status = 200, description = "Users list", body = Vec<UserResponse>)
    )
)]
#[get("/admin/users")]
pub async fn list_users(
    req: HttpRequest,
    query: web::Query<ListUsersQuery>,
    service: web::Data<Arc<AdminServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let token = extract_bearer_token(&req)?;
    validate_admin_role(&token).await?;

    let limit = query.limit.unwrap_or(50);
    let offset = query.offset.unwrap_or(0);

    let (users, _total) = service.list_users(limit, offset).await?;

    Ok(HttpResponse::Ok().json(users))
}

#[derive(serde::Deserialize)]
pub struct ListUsersQuery {
    pub limit: Option<i64>,
    pub offset: Option<i64>,
}

#[utoipa::path(
    get,
    path = "/api/admin/users/{id}",
    tag = "Admin",
    params(
        ("id" = String, Path, description = "User ID")
    ),
    security(
        ("bearer_auth" = [])
    ),
    responses(
        (status = 200, description = "User details", body = UserResponse),
        (status = 404, description = "User not found")
    )
)]
#[get("/admin/users/{id}")]
pub async fn get_user(
    req: HttpRequest,
    path: web::Path<String>,
    service: web::Data<Arc<AdminServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let token = extract_bearer_token(&req)?;
    validate_admin_role(&token).await?;

    let user = service.get_user(&path.into_inner()).await?;

    Ok(HttpResponse::Ok().json(UserResponse::from(user)))
}

#[utoipa::path(
    post,
    path = "/api/admin/users",
    tag = "Admin",
    request_body = CreateUserRequest,
    security(
        ("bearer_auth" = [])
    ),
    responses(
        (status = 201, description = "User created", body = MessageResponse)
    )
)]
#[post("/admin/users")]
pub async fn create_user(
    req: HttpRequest,
    body: web::Json<CreateUserRequest>,
    service: web::Data<Arc<AdminServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let token = extract_bearer_token(&req)?;
    validate_admin_role(&token).await?;

    let user = service
        .create_user(CreateUserData {
            email: body.email.clone(),
            username: body.username.clone(),
            password: body.password.clone(),
            first_name: body.first_name.clone(),
            last_name: body.last_name.clone(),
            phone: body.phone.clone(),
            role: body.role.clone(),
            network_id: body.network_id.clone(),
            station_id: body.station_id.clone(),
        })
        .await?;

    Ok(HttpResponse::Created().json(MessageResponse {
        id: Some(user.user_id),
        message: "User created.".to_string(),
    }))
}

#[utoipa::path(
    put,
    path = "/api/admin/users/{id}",
    tag = "Admin",
    params(
        ("id" = String, Path, description = "User ID")
    ),
    request_body = UpdateUserRequest,
    security(
        ("bearer_auth" = [])
    ),
    responses(
        (status = 200, description = "User updated", body = MessageResponse)
    )
)]
#[put("/admin/users/{id}")]
pub async fn update_user(
    req: HttpRequest,
    path: web::Path<String>,
    body: web::Json<UpdateUserRequest>,
    service: web::Data<Arc<AdminServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let token = extract_bearer_token(&req)?;
    validate_admin_role(&token).await?;

    service
        .update_user(
            &path.into_inner(),
            UpdateUserData {
                email: body.email.clone(),
                role: body.role.clone(),
                enabled: body.enabled,
            },
        )
        .await?;

    Ok(HttpResponse::Ok().json(MessageResponse {
        id: None,
        message: "User updated.".to_string(),
    }))
}

#[utoipa::path(
    delete,
    path = "/api/admin/users/{id}",
    tag = "Admin",
    params(
        ("id" = String, Path, description = "User ID")
    ),
    security(
        ("bearer_auth" = [])
    ),
    responses(
        (status = 204, description = "User deleted")
    )
)]
#[delete("/admin/users/{id}")]
pub async fn delete_user(
    req: HttpRequest,
    path: web::Path<String>,
    service: web::Data<Arc<AdminServiceImpl>>,
) -> Result<HttpResponse, AppError> {
    let token = extract_bearer_token(&req)?;
    validate_admin_role(&token).await?;

    service.delete_user(&path.into_inner()).await?;

    Ok(HttpResponse::NoContent().finish())
}

pub fn configure(cfg: &mut web::ServiceConfig) {
    cfg.service(list_users)
        .service(get_user)
        .service(create_user)
        .service(update_user)
        .service(delete_user);
}
