use pyo3::prelude::*;
use pyo3_async_runtimes;

use crate::agent_runtime;
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
    pub output: Option<String>,
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
    pub name: String,
    #[pyo3(get, set)]
    pub model: String,
    #[pyo3(get, set)]
    pub ollama_url: String,
    #[pyo3(get, set)]
    pub temperature: f32,
    #[pyo3(get, set)]
    pub timeout_seconds: u64,
}

#[pymethods]
impl PyAgentConfig {
    #[new]
    fn new(name: String, model: String, ollama_url: String, temperature: f32, timeout_seconds: u64) -> Self {
        PyAgentConfig {
            name,
            model,
            ollama_url,
            temperature,
            timeout_seconds,
        }
    }
}

impl From<PyAgentConfig> for AgentConfig {
    fn from(py_config: PyAgentConfig) -> Self {
        AgentConfig {
            name: py_config.name,
            model: py_config.model,
            ollama_url: py_config.ollama_url,
            temperature: py_config.temperature,
            timeout_seconds: py_config.timeout_seconds,
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
            execution_time: result.duration_ms as f64,
        }
    }
}

/// Execute multiple agents in parallel from Python
#[pyfunction]
fn execute_agents_parallel(
    py: Python<'_>,
    agents: Vec<(String, PyAgentConfig)>,
    input_data: String,
) -> PyResult<Bound<'_, PyAny>> {
    let rust_agents: Vec<RustAgent> = agents
        .into_iter()
        .map(|(id, mut config)| {
            config.name = id;
            RustAgent::new(config.into()).unwrap()
        })
        .collect();

    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let tasks = vec![input_data; rust_agents.len()];
        let results = execute_parallel(rust_agents, tasks).await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        let py_results: Vec<PyAgentResult> =
            results.into_iter().map(PyAgentResult::from).collect();
        Ok(py_results)
    })
}

/// Execute a single agent from Python
#[pyfunction]
fn execute_agent(py: Python<'_>, agent_id: String, mut config: PyAgentConfig, input_data: String) -> PyResult<Bound<'_, PyAny>> {
    config.name = agent_id;
    let agent = RustAgent::new(config.into()).unwrap();
    
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let result = agent.execute(&input_data).await
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(PyAgentResult::from(result))
    })
}

/// Batch execute agents with different inputs
#[pyfunction]
fn execute_agents_batch(
    py: Python<'_>,
    agent_configs: Vec<(String, PyAgentConfig)>,
    inputs: Vec<String>,
) -> PyResult<Bound<'_, PyAny>> {
    pyo3_async_runtimes::tokio::future_into_py(py, async move {
        let mut all_results = Vec::new();

        for input in inputs {
            let rust_agents: Vec<RustAgent> = agent_configs
                .iter()
                .map(|(id, config)| {
                    let mut config = config.clone();
                    config.name = id.clone();
                    RustAgent::new(config.into()).unwrap()
                })
                .collect();

            let tasks = vec![input; rust_agents.len()];
            let results = execute_parallel(rust_agents, tasks).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
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
fn agent_runtime_py(py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(execute_agents_parallel, py)?)?;
    m.add_function(wrap_pyfunction!(execute_agent, py)?)?;
    m.add_function(wrap_pyfunction!(execute_agents_batch, py)?)?;
    m.add_function(wrap_pyfunction!(get_metrics, py)?)?;
    m.add_class::<PyAgentConfig>()?;
    m.add_class::<PyAgentResult>()?;
    m.add_class::<PyExecutionMetrics>()?;
    Ok(())
}
