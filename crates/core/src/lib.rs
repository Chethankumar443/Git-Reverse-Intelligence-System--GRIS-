use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use thiserror::Error;
use uuid::Uuid;

/// Unified Application Error hierarchy.
#[derive(Debug, Error)]
pub enum AppError {
    #[error("Authentication failed: {0}")]
    AuthError(String),

    #[error("Permission denied: required scope '{0}' is missing")]
    PermissionDenied(String),

    #[error("Resource not found: {0}")]
    NotFound(String),

    #[error("Invalid request input: {0}")]
    ValidationError(String),

    #[error("Database error: {0}")]
    DatabaseError(String),

    #[error("LLM Provider failure: {0}")]
    ProviderError(String),

    #[error("Internal system error: {0}")]
    InternalError(String),
}

/// Member classification in the collaborative workspace.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum MemberType {
    Human,
    Agent,
}

/// Fine-grained permission scopes for AI Agents and Users.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "snake_case")]
pub enum PermissionScope {
    ReadChannels,
    PostMessages,
    ReviewPatches,
    TriageIssues,
    QueryKnowledgeBase,
    RunAnalysis,
    ManageAgents,
    SystemAdmin,
}

/// Agent Capability Definition & Metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentProfile {
    pub id: Uuid,
    pub name: String,
    pub slug: String,
    pub description: Option<String>,
    pub avatar_emoji: String,
    pub capabilities: Vec<PermissionScope>,
    pub llm_provider: Option<String>,
    pub llm_model: Option<String>,
    pub is_active: bool,
    pub created_at: DateTime<Utc>,
}

/// Audit Log Record representing any action executed by a human or agent.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditRecord {
    pub id: Uuid,
    pub actor_id: Uuid,
    pub actor_type: MemberType,
    pub action: String,
    pub resource_type: String,
    pub resource_id: Option<String>,
    pub scope_validated: PermissionScope,
    pub detail: serde_json::Value,
    pub timestamp: DateTime<Utc>,
}
