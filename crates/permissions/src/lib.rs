use git_reverse_core::{AppError, PermissionScope};
use tracing::{error, info};

/// Enforces fail-closed scope checking.
/// Returns Ok(()) if the granted_scopes list contains the required_scope.
/// Otherwise returns Err(AppError::PermissionDenied).
pub fn authorize(
    granted_scopes: &[PermissionScope],
    required_scope: &PermissionScope,
) -> Result<(), AppError> {
    // Admin scope grants all actions
    if granted_scopes.contains(&PermissionScope::SystemAdmin) {
        info!("Permission granted via SystemAdmin scope");
        return Ok(());
    }

    if granted_scopes.contains(required_scope) {
        Ok(())
    } else {
        error!(
            "FAIL-CLOSED: Required scope '{:?}' not present in granted scopes: {:?}",
            required_scope, granted_scopes
        );
        Err(AppError::PermissionDenied(format!("{:?}", required_scope)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fail_closed_permission_check() {
        let granted = vec![PermissionScope::ReadChannels, PermissionScope::PostMessages];
        assert!(authorize(&granted, &PermissionScope::PostMessages).is_ok());
        assert!(authorize(&granted, &PermissionScope::RunAnalysis).is_err());
    }

    #[test]
    fn test_admin_override() {
        let granted = vec![PermissionScope::SystemAdmin];
        assert!(authorize(&granted, &PermissionScope::RunAnalysis).is_ok());
    }
}
