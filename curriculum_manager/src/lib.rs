use serde::{Serialize, Deserialize};
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillNode {
    pub id: String,
    pub name: String,
    pub prerequisites: Vec<String>,
    pub dna_path: String, // Ruta al Guerrero Campeón actual
    pub level: u32,
}

pub struct CurriculumManager {
    pub skill_tree: HashMap<String, SkillNode>,
    pub active_learning_path: Vec<String>,
}

impl CurriculumManager {
    pub fn new() -> Self {
        Self {
            skill_tree: HashMap::new(),
            active_learning_path: vec![],
        }
    }

    pub fn add_skill(&mut self, node: SkillNode) {
        self.skill_tree.insert(node.id.clone(), node);
    }

    /// Calcula la ruta de aprendizaje óptima para un objetivo
    pub fn get_path_to(&self, target_id: &str) -> Vec<String> {
        let mut path = vec![];
        let mut visited = HashSet::new();
        self.traverse(target_id, &mut path, &mut visited);
        path
    }

    fn traverse(&self, current: &str, path: &mut Vec<String>, visited: &mut HashSet<String>) {
        if visited.contains(current) { return; }
        if let Some(node) = self.skill_tree.get(current) {
            for pre in &node.prerequisites {
                self.traverse(pre, path, visited);
            }
            path.push(current.to_string());
            visited.insert(current.to_string());
        }
    }
}
