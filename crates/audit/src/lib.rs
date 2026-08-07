use chrono::Utc;
use git_reverse_core::{AuditRecord, MemberType, PermissionScope};
use tracing::info;
use uuid::Uuid;

/// Constructs an immutable AuditRecord payload.
pub fn create_audit_entry(
    actor_id: Uuid,
    actor_type: MemberType,
    action: &str,
    resource_type: &str,
    resource_id: Option<String>,
    scope_validated: PermissionScope,
    detail: serde_json::Value,
) -> AuditRecord {
    let entry = AuditRecord {
        id: Uuid::new_v4(),
        actor_id,
        actor_type,
        action: action.to_string(),
        resource_type: resource_type.to_string(),
        resource_id,
        scope_validated,
        detail,
        timestamp: Utc::now(),
    };

    info!(
        audit_id = %entry.id,
        actor_id = %entry.actor_id,
        action = %entry.action,
        "Audit trail recorded"
    );

    entry
}
