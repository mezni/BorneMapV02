// =============================================================================
// src/core/auth.rs - JWT Authentication with Keycloak (FIXED)
// =============================================================================
use crate::core::errors::{AppError, AppResult};
use actix_web::HttpRequest;
use jsonwebtoken::{decode, decode_header, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TokenClaims {
    pub sub: String,
    pub exp: i64,
    pub iat: i64,
    #[serde(default)]
    pub roles: Vec<String>,
    #[serde(default)]
    pub realm_access: Option<RealmAccess>,
    pub email: Option<String>,
    pub preferred_username: Option<String>,
    pub iss: Option<String>,
    pub aud: Option<serde_json::Value>,  // Can be string or array
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct RealmAccess {
    #[serde(default)]
    pub roles: Vec<String>,
}

impl TokenClaims {
    pub fn get_roles(&self) -> Vec<String> {
        // Try realm_access.roles first (Keycloak default)
        if let Some(ref realm) = self.realm_access {
            if !realm.roles.is_empty() {
                return realm.roles.clone();
            }
        }
        
        // Fallback to direct roles array
        self.roles.clone()
    }
}

#[derive(Debug, Clone, Deserialize)]
struct JwksKey {
    kid: String,
    n: String,
    e: String,
}

#[derive(Debug, Clone, Deserialize)]
struct Jwks {
    keys: Vec<JwksKey>,
}

pub struct JwtValidator {
    jwks_url: String,
    jwt_issuer: String,
    jwks_cache: Arc<RwLock<Option<Jwks>>>,
    http_client: reqwest::Client,
}

impl JwtValidator {
    pub fn new(jwks_url: String, jwt_issuer: String) -> Self {
        Self {
            jwks_url,
            jwt_issuer,
            jwks_cache: Arc::new(RwLock::new(None)),
            http_client: reqwest::Client::new(),
        }
    }

    async fn fetch_jwks(&self) -> AppResult<Jwks> {
        let response = self
            .http_client
            .get(&self.jwks_url)
            .send()
            .await
            .map_err(|e| AppError::InternalError(format!("Failed to fetch JWKS: {}", e)))?;

        let jwks: Jwks = response
            .json()
            .await
            .map_err(|e| AppError::InternalError(format!("Failed to parse JWKS: {}", e)))?;

        Ok(jwks)
    }

    async fn get_jwks(&self) -> AppResult<Jwks> {
        {
            let cache = self.jwks_cache.read().await;
            if let Some(ref jwks) = *cache {
                return Ok(jwks.clone());
            }
        }

        let jwks = self.fetch_jwks().await?;
        let mut cache = self.jwks_cache.write().await;
        *cache = Some(jwks.clone());
        Ok(jwks)
    }

    pub async fn validate_token(&self, token: &str) -> AppResult<TokenClaims> {
        // Decode header to get kid
        let header = decode_header(token)?;
        let kid = header
            .kid
            .ok_or_else(|| AppError::Unauthorized("Missing kid in token header".to_string()))?;

        // Get JWKS
        let jwks = self.get_jwks().await?;

        // Find matching key
        let key = jwks
            .keys
            .iter()
            .find(|k| k.kid == kid)
            .ok_or_else(|| AppError::Unauthorized("Key not found in JWKS".to_string()))?;

        // Create decoding key
        let decoding_key = DecodingKey::from_rsa_components(&key.n, &key.e)?;

        // Validate token - RELAXED VALIDATION
        let mut validation = Validation::new(Algorithm::RS256);
        validation.set_issuer(&[&self.jwt_issuer]);
        
        // Don't validate audience - Keycloak tokens can have various audiences
        validation.validate_aud = false;
        
        // Allow some clock skew (60 seconds)
        validation.leeway = 60;

        let token_data = decode::<TokenClaims>(token, &decoding_key, &validation)?;

        Ok(token_data.claims)
    }

    pub async fn validate_admin(&self, token: &str) -> AppResult<TokenClaims> {
        let claims = self.validate_token(token).await?;

        let roles = claims.get_roles();
        
        if !roles.contains(&"admin".to_string()) {
            return Err(AppError::Forbidden(format!(
                "Admin role required. Found roles: {:?}",
                roles
            )));
        }

        Ok(claims)
    }
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

// Middleware-like function to extract and validate admin token
pub async fn require_admin_auth(
    req: &HttpRequest,
    validator: &JwtValidator,
) -> AppResult<TokenClaims> {
    let token = extract_bearer_token(req)?;
    validator.validate_admin(&token).await
}