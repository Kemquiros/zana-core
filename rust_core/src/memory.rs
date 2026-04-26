use serde::{Serialize, Deserialize};
use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;

#[derive(Serialize, Deserialize, Clone)]
pub struct Document {
    pub id: String,
    pub embedding: Vec<f64>,
    pub metadata: String,
}

#[derive(Serialize, Deserialize, Default)]
pub struct VectorIndex {
    documents: Vec<Document>,
}

impl VectorIndex {
    pub fn new() -> Self {
        Self {
            documents: Vec::new(),
        }
    }

    pub fn add(&mut self, id: String, embedding: Vec<f64>, metadata: String) {
        self.documents.push(Document {
            id,
            embedding,
            metadata,
        });
    }

    pub fn delete(&mut self, id: &str) {
        self.documents.retain(|doc| doc.id != id);
    }

    fn cosine_similarity(a: &[f64], b: &[f64]) -> f64 {
        if a.len() != b.len() || a.is_empty() {
            return 0.0;
        }
        let mut dot_product = 0.0;
        let mut norm_a = 0.0;
        let mut norm_b = 0.0;
        for (x, y) in a.iter().zip(b.iter()) {
            dot_product += x * y;
            norm_a += x * x;
            norm_b += y * y;
        }
        if norm_a == 0.0 || norm_b == 0.0 {
            0.0
        } else {
            dot_product / (norm_a.sqrt() * norm_b.sqrt())
        }
    }

    pub fn search(&self, query: &[f64], top_k: usize) -> Vec<(String, f64, String)> {
        let mut results: Vec<(String, f64, String)> = self.documents
            .iter()
            .map(|doc| {
                let similarity = Self::cosine_similarity(query, &doc.embedding);
                (doc.id.clone(), similarity, doc.metadata.clone())
            })
            .collect();

        // Sort in descending order of similarity
        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        
        results.into_iter().take(top_k).collect()
    }

    pub fn save(&self, path: &str) -> std::io::Result<()> {
        let json = serde_json::to_string(&self)?;
        let mut file = File::create(Path::new(path))?;
        file.write_all(json.as_bytes())?;
        Ok(())
    }

    pub fn load(path: &str) -> std::io::Result<Self> {
        let mut file = File::open(Path::new(path))?;
        let mut json = String::new();
        file.read_to_string(&mut json)?;
        let index: VectorIndex = serde_json::from_str(&json)?;
        Ok(index)
    }
}
