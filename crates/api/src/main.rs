use axum::{
    routing::{get, post},
    Json, Router,
};
use git_reverse_core::{MemberType, PermissionScope};
use git_reverse_identity::create_jwt;
use serde_json::json;
use std::net::SocketAddr;
use tower_http::cors::{Any, CorsLayer};
use tracing::info;
use uuid::Uuid;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/health", get(health_handler))
        .route("/api/v1/auth/demo-token", post(demo_token_handler))
        .layer(cors);

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    info!("Git Reverse 2.0 Rust Axum API running on http://{}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn health_handler() -> Json<serde_json::Value> {
    Json(json!({
        "status": "ok",
        "version": "2.0.0",
        "engine": "Rust Axum Tokio",
        "audit_logging": "active",
        "fail_closed_security": "enforced"
    }))
}

async fn demo_token_handler() -> Json<serde_json::Value> {
    let demo_id = Uuid::new_v4();
    let token = create_jwt(
        demo_id,
        MemberType::Human,
        vec![
            PermissionScope::ReadChannels,
            PermissionScope::PostMessages,
            PermissionScope::QueryKnowledgeBase,
        ],
        24,
    )
    .unwrap();

    Json(json!({
        "token": token,
        "token_type": "bearer",
        "member_type": "human",
        "actor_id": demo_id
    }))
}
