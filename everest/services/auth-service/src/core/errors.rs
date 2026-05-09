use actix_web::{http::StatusCode, HttpResponse, ResponseError};
use serde::Serialize;
use std::fmt;

#[derive(Debug)]
pub enum AppError {
    // Database
    DatabaseError(String),
    NotFound(String),

    // Validation
    ValidationError(String),
    Conflict(String),

    // Authentication
    Unauthorized(String),
    Forbidden(String),

    // External services
    KeycloakError(String),
    NetworkError(String),

    // Business logic
    VerificationExpired,
    VerificationInvalid,
    ResendLimitExceeded,
    InvitationExpired,
    InvitationInvalid,

    // Generic
    InternalError(String),
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::DatabaseError(msg) => write!(f, "Database error: {}", msg),
            Self::NotFound(msg) => write!(f, "Not found: {}", msg),
            Self::ValidationError(msg) => write!(f, "Validation error: {}", msg),
            Self::Conflict(msg) => write!(f, "Conflict: {}", msg),
            Self::Unauthorized(msg) => write!(f, "Unauthorized: {}", msg),
            Self::Forbidden(msg) => write!(f, "Forbidden: {}", msg),
            Self::KeycloakError(msg) => write!(f, "Keycloak error: {}", msg),
            Self::NetworkError(msg) => write!(f, "Network error: {}", msg),
            Self::VerificationExpired => write!(f, "Verification token expired"),
            Self::VerificationInvalid => write!(f, "Invalid verification token"),
            Self::ResendLimitExceeded => write!(f, "Resend limit exceeded"),
            Self::InvitationExpired => write!(f, "Invitation expired"),
            Self::InvitationInvalid => write!(f, "Invalid invitation"),
            Self::InternalError(msg) => write!(f, "Internal error: {}", msg),
        }
    }
}

impl std::error::Error for AppError {}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
    message: String,
}

impl ResponseError for AppError {
    fn status_code(&self) -> StatusCode {
        match self {
            Self::NotFound(_) => StatusCode::NOT_FOUND,
            Self::ValidationError(_) => StatusCode::BAD_REQUEST,
            Self::Conflict(_) => StatusCode::CONFLICT,
            Self::Unauthorized(_) => StatusCode::UNAUTHORIZED,
            Self::Forbidden(_) => StatusCode::FORBIDDEN,
            Self::VerificationExpired => StatusCode::GONE,
            Self::VerificationInvalid => StatusCode::BAD_REQUEST,
            Self::ResendLimitExceeded => StatusCode::TOO_MANY_REQUESTS,
            Self::InvitationExpired => StatusCode::GONE,
            Self::InvitationInvalid => StatusCode::NOT_FOUND,
            _ => StatusCode::INTERNAL_SERVER_ERROR,
        }
    }

    fn error_response(&self) -> HttpResponse {
        let status = self.status_code();
        let error_type = match self {
            Self::DatabaseError(_) => "database_error",
            Self::NotFound(_) => "not_found",
            Self::ValidationError(_) => "validation_error",
            Self::Conflict(_) => "conflict",
            Self::Unauthorized(_) => "unauthorized",
            Self::Forbidden(_) => "forbidden",
            Self::KeycloakError(_) => "keycloak_error",
            Self::NetworkError(_) => "network_error",
            Self::VerificationExpired => "verification_expired",
            Self::VerificationInvalid => "verification_invalid",
            Self::ResendLimitExceeded => "resend_limit_exceeded",
            Self::InvitationExpired => "invitation_expired",
            Self::InvitationInvalid => "invitation_invalid",
            Self::InternalError(_) => "internal_error",
        };

        HttpResponse::build(status).json(ErrorResponse {
            error: error_type.to_string(),
            message: self.to_string(),
        })
    }
}

pub type AppResult<T> = Result<T, AppError>;

// Conversions
impl From<sqlx::Error> for AppError {
    fn from(err: sqlx::Error) -> Self {
        match err {
            sqlx::Error::RowNotFound => Self::NotFound("Record not found".to_string()),
            _ => Self::DatabaseError(err.to_string()),
        }
    }
}

impl From<crate::infrastructure::keycloak_client::AppError> for AppError {
    fn from(err: crate::infrastructure::keycloak_client::AppError) -> Self {
        match err {
            crate::infrastructure::keycloak_client::AppError::KeycloakError(msg) => {
                Self::KeycloakError(msg)
            }
            crate::infrastructure::keycloak_client::AppError::NetworkError(msg) => {
                Self::NetworkError(msg)
            }
            crate::infrastructure::keycloak_client::AppError::AuthenticationError(msg) => {
                Self::Unauthorized(msg)
            }
            crate::infrastructure::keycloak_client::AppError::NotFound(msg) => Self::NotFound(msg),
            crate::infrastructure::keycloak_client::AppError::Unauthorized(msg) => {
                Self::Unauthorized(msg)
            }
        }
    }
}
