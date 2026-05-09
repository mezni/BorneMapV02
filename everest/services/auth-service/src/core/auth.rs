use crate::core::errors::{AppError, AppResult};
use actix_web::HttpRequest;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TokenClaims {
    pub sub: String,
    pub exp: i64,
    pub iat: i64,
    pub roles: Vec<String>,
    pub email: Option<String>,
    pub preferred_username: Option<String>,
}

pub fn extract_bearer_token(req: &HttpRequest) -> AppResult<String> {
    req.headers()
        .get("Authorization")
        .and_then(|h| h.to_str().ok())
        .and_then(|auth| auth.strip_prefix("Bearer "))
        .map(|token| token.to_string())
        .ok_or_else(|| {
            AppError::Unauthorized("Missing or invalid Authorization header".to_string())
        })
}

pub async fn validate_admin_role(token: &str) -> AppResult<TokenClaims> {
    let claims = decode_token(token)?;

    if !claims.roles.contains(&"admin".to_string()) {
        return Err(AppError::Forbidden("Admin role required".to_string()));
    }

    Ok(claims)
}

fn decode_token(_token: &str) -> AppResult<TokenClaims> {
    // TODO: Implement proper JWT decoding with jsonwebtoken crate
    // For now, return a mock admin user for development
    // In production, you MUST implement proper JWT validation:
    //
    // use jsonwebtoken::{decode, DecodingKey, Validation, Algorithm};
    //
    // 1. Fetch Keycloak's public key from:
    //    GET {keycloak_url}/realms/{realm}/protocol/openid-connect/certs
    //
    // 2. Decode and verify:
    //    let validation = Validation::new(Algorithm::RS256);
    //    let token_data = decode::<TokenClaims>(
    //        token,
    //        &DecodingKey::from_rsa_components(modulus, exponent)?,
    //        &validation
    //    )?;
    //    return Ok(token_data.claims);

    // TEMPORARY MOCK FOR DEVELOPMENT ONLY
    Ok(TokenClaims {
        sub: "mock-user-id".to_string(),
        exp: 9999999999,
        iat: 1000000000,
        roles: vec!["admin".to_string()],
        email: Some("admin@example.com".to_string()),
        preferred_username: Some("admin".to_string()),
    })
}
