use chrono::{Duration, Utc};
use git_reverse_core::{AppError, MemberType, PermissionScope};
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

const JWT_SECRET: &[u8] = b"git-reverse-2-super-secret-key-change-in-production";

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub member_type: MemberType,
    pub scopes: Vec<PermissionScope>,
    pub exp: usize,
    pub iat: usize,
}

pub fn create_jwt(
    actor_id: Uuid,
    member_type: MemberType,
    scopes: Vec<PermissionScope>,
    duration_hours: i64,
) -> Result<String, AppError> {
    let now = Utc::now();
    let exp = now + Duration::hours(duration_hours);

    let claims = Claims {
        sub: actor_id.to_string(),
        member_type,
        scopes,
        exp: exp.timestamp() as usize,
        iat: now.timestamp() as usize,
    };

    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(JWT_SECRET),
    )
    .map_err(|e| AppError::AuthError(e.to_string()))
}

pub fn verify_jwt(token: &str) -> Result<Claims, AppError> {
    decode::<Claims>(
        token,
        &DecodingKey::from_secret(JWT_SECRET),
        &Validation::default(),
    )
    .map(|data| data.claims)
    .map_err(|e| AppError::AuthError(format!("Invalid token: {}", e)))
}
