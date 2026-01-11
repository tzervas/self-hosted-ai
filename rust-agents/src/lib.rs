// Main library entry point - exposes both Rust API and Python bindings

pub mod agent_runtime;

// Re-export main Rust types for Rust consumers
pub use agent_runtime::{execute_parallel, AgentConfig, AgentResult, RustAgent};

// Python bindings are compiled separately when building as a Python extension
#[cfg(feature = "python")]
pub mod python_bindings;
