// Rust-based agent runtime for performance-critical operations

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Serialize, Deserialize)]
pub struct AgentConfig {
    pub name: String,
    pub model: String,
    pub ollama_url: String,
    pub temperature: f32,
    pub timeout_seconds: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AgentResult {
    pub agent_id: String,
    pub status: String,
    pub output: Option<String>,
    pub error: Option<String>,
    pub duration_ms: u128,
}

pub struct RustAgent {
    config: AgentConfig,
    client: reqwest::Client,
}

impl RustAgent {
    pub fn new(config: AgentConfig) -> Result<Self> {
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(config.timeout_seconds))
            .build()?;

        Ok(Self { config, client })
    }

    pub async fn execute(&self, task: &str) -> Result<AgentResult> {
        let start = std::time::Instant::now();

        // Call Ollama API
        let response = self
            .client
            .post(format!("{}/api/generate", self.config.ollama_url))
            .json(&serde_json::json!({
                "model": self.config.model,
                "prompt": task,
                "temperature": self.config.temperature,
                "stream": false,
            }))
            .send()
            .await?;

        let result: serde_json::Value = response.json().await?;
        let duration = start.elapsed().as_millis();

        Ok(AgentResult {
            agent_id: uuid::Uuid::new_v4().to_string(),
            status: "completed".to_string(),
            output: result
                .get("response")
                .and_then(|v| v.as_str())
                .map(String::from),
            error: None,
            duration_ms: duration,
        })
    }
}

// Parallel processing for multiple agents
pub async fn execute_parallel(
    agents: Vec<RustAgent>,
    tasks: Vec<String>,
) -> Result<Vec<AgentResult>> {
    use tokio::task::JoinSet;

    let mut set = JoinSet::new();

    for (agent, task) in agents.into_iter().zip(tasks.into_iter()) {
        set.spawn(async move { agent.execute(&task).await });
    }

    let mut results = Vec::new();
    while let Some(res) = set.join_next().await {
        results.push(res??);
    }

    Ok(results)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_config() {
        let config = AgentConfig {
            name: "test".to_string(),
            model: "qwen2.5-coder:14b".to_string(),
            ollama_url: "http://localhost:11434".to_string(),
            temperature: 0.7,
            timeout_seconds: 60,
        };

        assert_eq!(config.name, "test");
        assert_eq!(config.temperature, 0.7);
    }
}
