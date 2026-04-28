use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

#[pyclass]
#[derive(Serialize, Deserialize, Clone)]
pub struct PyProjectProcessor {
    pub default_namespace: String,
}

#[pymethods]
impl PyProjectProcessor {
    #[new]
    fn new(namespace: String) -> Self {
        Self { default_namespace: namespace }
    }

    /// Fast validation and hashing of a project payload
    fn validate_and_hash(&self, project_name: &str, files_count: usize) -> PyResult<String> {
        if project_name.trim().is_empty() {
            return Err(PyValueError::new_err("Project name cannot be empty"));
        }
        let mut hasher = DefaultHasher::new();
        project_name.hash(&mut hasher);
        files_count.hash(&mut hasher);
        self.default_namespace.hash(&mut hasher);
        
        Ok(format!("{:x}", hasher.finish()))
    }
    
    /// Compute a deterministic hash for a file path to prevent duplicates
    fn compute_file_hash(&self, file_path: &str) -> String {
        let mut hasher = DefaultHasher::new();
        file_path.hash(&mut hasher);
        format!("{:x}", hasher.finish())
    }
}