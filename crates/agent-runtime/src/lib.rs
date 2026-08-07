use git_reverse_core::{AgentProfile, AppError, MemberType, PermissionScope};
use git_reverse_permissions::authorize;
use git_reverse_audit::create_audit_entry;
use serde::{Deserialize, Serialize};
use tracing::info;

#[derive(Debug, Serialize, Deserialize)]
pub struct LLMCompletionRequest {
    pub prompt: String,
    pub system_prompt: Option<String>,
    pub temperature: Option<f32>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LLMCompletionResponse {
    pub content: String,
    pub model: String,
    pub tokens_used: u32,
}

/// Executes an AI Agent task with pre-invocation fail-closed scope checking.
pub async fn execute_agent_task(
    agent: &AgentProfile,
    required_scope: PermissionScope,
    request: LLMCompletionRequest,
) -> Result<LLMCompletionResponse, AppError> {
    // Step 1: Pre-invocation scope validation (Fail-Closed)
    authorize(&agent.capabilities, &required_scope)?;

    info!(
        agent_id = %agent.id,
        agent_name = %agent.name,
        scope = ?required_scope,
        "Agent pre-invocation scope check passed"
    );

    // Step 2: Audit entry generation
    let _audit = create_audit_entry(
        agent.id,
        MemberType::Agent,
        "execute_llm_task",
        "agent_runtime",
        Some(agent.id.to_string()),
        required_scope,
        serde_json::json!({
            "prompt_length": request.prompt.len(),
            "model": agent.llm_model.as_deref().unwrap_or("default")
        }),
    );

    // Step 3: Simulated LLM call return (production plugs into OpenRouter/reqwest)
    Ok(LLMCompletionResponse {
        content: format!(
            "[AI Agent Response from {}]: Processed request with context.",
            agent.name
        ),
        model: agent
            .llm_model
            .clone()
            .unwrap_or_else(|| "cohere/north-mini-code:free".to_string()),
        tokens_used: 142,
    })
}
