use pyo3::prelude::*;
use pyo3_asyncio;
use std::collections::HashMap;

mod agent_runtime;
use agent_runtime::{execute_parallel, AgentConfig, RustAgent};

/// Python-facing agent result
#[pyclass]
#[derive(Clone)]
pub struct PyAgentResult {
    #[pyo3(get)]
    pub agent_id: String,
    #[pyo3(get)]
    pub status: String,
    #[pyo3(get)]
    pub output: String,
    #[pyo3(get)]
    pub error: Option<String>,
    #[pyo3(get)]
    pub execution_time: f64,
}

/// Python-facing agent configuration
#[pyclass]
#[derive(Clone)]
pub struct PyAgentConfig {
    #[pyo3(get, set)]
    pub model: String,
    #[pyo3(get, set)]
    pub temperature: f64,
    #[pyo3(get, set)]
    pub timeout: u64,
    #[pyo3(get, set)]
    pub max_tokens: Option<usize>,
}

#[pymethods]
impl PyAgentConfig {
    #[new]
    fn new(model: String, temperature: f64, timeout: u64, max_tokens: Option<usize>) -> Self {
        PyAgentConfig {
            model,
            temperature,
            timeout,
            max_tokens,
        }
    }
}

impl From<PyAgentConfig> for AgentConfig {
    fn from(py_config: PyAgentConfig) -> Self {
        AgentConfig {
            model: py_config.model,
            temperature: py_config.temperature,
            timeout: py_config.timeout,
            max_tokens: py_config.max_tokens,
        }
    }
}

impl From<agent_runtime::AgentResult> for PyAgentResult {
    fn from(result: agent_runtime::AgentResult) -> Self {
        PyAgentResult {
            agent_id: result.agent_id,
            status: result.status,
            output: result.output,
            error: result.error,
            execution_time: result.execution_time,
        }
    }
}

/// Execute multiple agents in parallel from Python
#[pyfunction]
fn execute_agents_parallel(
    py: Python,
    agents: Vec<(String, PyAgentConfig)>,
    input_data: String,
) -> PyResult<&PyAny> {
    let rust_agents: Vec<RustAgent> = agents
        .into_iter()
        .map(|(id, config)| RustAgent::new(id, config.into()))
        .collect();

    pyo3_asyncio::tokio::future_into_py(py, async move {
        let results = execute_parallel(rust_agents, &input_data).await;
        let py_results: Vec<PyAgentResult> =
            results.into_iter().map(PyAgentResult::from).collect();
        Ok(py_results)
    })
}

/// Execute a single agent from Python
#[pyfunction]
fn execute_agent(py: Python, agent_id: String, config: PyAgentConfig, input_data: String) -> PyResult<&PyAny> {
    let agent = RustAgent::new(agent_id, config.into());
    
    pyo3_asyncio::tokio::future_into_py(py, async move {
        let result = agent.execute(&input_data).await;
        Ok(PyAgentResult::from(result))
    })
}

/// Batch execute agents with different inputs
#[pyfunction]
fn execute_agents_batch(
    py: Python,
    agent_configs: Vec<(String, PyAgentConfig)>,
    inputs: Vec<String>,
) -> PyResult<&PyAny> {
    pyo3_asyncio::tokio::future_into_py(py, async move {
        let mut all_results = Vec::new();

        for input in inputs {
            let rust_agents: Vec<RustAgent> = agent_configs
                .iter()
                .map(|(id, config)| RustAgent::new(id.clone(), config.clone().into()))
                .collect();

            let results = execute_parallel(rust_agents, &input).await;
            all_results.extend(results.into_iter().map(PyAgentResult::from));
        }

        Ok(all_results)
    })
}

/// Performance metrics for agent execution
#[pyclass]
#[derive(Clone)]
pub struct PyExecutionMetrics {
    #[pyo3(get)]
    pub total_agents: usize,
    #[pyo3(get)]
    pub successful: usize,
    #[pyo3(get)]
    pub failed: usize,
    #[pyo3(get)]
    pub total_time: f64,
    #[pyo3(get)]
    pub avg_time: f64,
}

/// Get execution metrics from results
#[pyfunction]
fn get_metrics(results: Vec<PyAgentResult>) -> PyExecutionMetrics {
    let total_agents = results.len();
    let successful = results.iter().filter(|r| r.status == "completed").count();
    let failed = total_agents - successful;
    let total_time: f64 = results.iter().map(|r| r.execution_time).sum();
    let avg_time = if total_agents > 0 {
        total_time / total_agents as f64
    } else {
        0.0
    };

    PyExecutionMetrics {
        total_agents,
        successful,
        failed,
        total_time,
        avg_time,
    }
}

/// Python module definition
#[pymodule]
fn agent_runtime_py(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(execute_agents_parallel, m)?)?;
    m.add_function(wrap_pyfunction!(execute_agent, m)?)?;
    m.add_function(wrap_pyfunction!(execute_agents_batch, m)?)?;
    m.add_function(wrap_pyfunction!(get_metrics, m)?)?;
    m.add_class::<PyAgentConfig>()?;
    m.add_class::<PyAgentResult>()?;
    m.add_class::<PyExecutionMetrics>()?;
    Ok(())
}
