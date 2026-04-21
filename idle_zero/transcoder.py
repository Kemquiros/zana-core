import yaml
import json
import uuid
from pathlib import Path
import re
import os

# Configuration
SOURCE_DIR = os.getenv("TRANSCODER_SOURCE_DIR", str(Path(__file__).parent / "source_docs"))
OUTPUT_DIR = os.getenv("TRANSCODER_OUTPUT_DIR", str(Path(__file__).parent / "seeds"))

def parse_md_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 1. Try to extract YAML block
        match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            yaml_text = match.group(1)
            yaml_clean = "\n".join([line for line in yaml_text.splitlines() if not line.strip().startswith('#')])
            metadata = yaml.safe_load(yaml_clean)
            return metadata
        
        # 2. If no YAML, infer from Markdown structure
        # Title usually starts with #
        title_match = re.search(r'^#\s+(.*)', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else file_path.stem
        
        # Description usually after ## Descripción
        desc_match = re.search(r'## Descripción\s*\n(.*?)\n', content, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ""
        
        # Build inferred metadata
        metadata = {
            "name": f"agora_{re.sub(r'[^a-zA-Z0-9_]', '_', title.lower())}",
            "version": "0.1.0-alpha",
            "description": description,
            "intent": [re.sub(r'[^a-zA-Z0-9_]', '_', title.lower())],
            "adk_schema": {
                "parameters": {"type": "object", "properties": {}, "required": []},
                "returns": {"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]}
            }
        }
        return metadata
        
    except Exception as e:
        print(f"  [!] Error al procesar {file_path.name}: {e}")
        return None

def create_warrior_seed(metadata):
    if not metadata or 'name' not in metadata:
        return None
        
    seed = {
        "id": f"seed_{metadata['name']}",
        "generation": 0,
        "setup": [],
        "predict": [],
        "learn": [],
        "fitness": 0.0,
        "metadata": {
            "version": metadata.get('version', '1.0.0'),
            "intents": metadata.get('intent', []),
            "schema": metadata.get('adk_schema', {}),
            "description": metadata.get('description', '')
        }
    }
    return seed

def batch_transcode():
    print(f"🔱 [ZANA AUTO-TRANSCODER] Iniciando asimilación inteligente...")
    
    source_path = Path(SOURCE_DIR)
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    
    md_files = list(source_path.rglob("*.md"))
    print(f"🔍 Encontrados {len(md_files)} archivos potenciales.")
    
    success_count = 0
    error_count = 0
    
    for md_file in md_files:
        meta = parse_md_content(md_file)
        if not meta:
            error_count += 1
            continue
            
        seed = create_warrior_seed(meta)
        if not seed:
            error_count += 1
            continue
            
        # Use name as filename to avoid duplicates/collisions
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', meta['name'].lower())
        output_file = output_path / f"{safe_name}.json"
        
        # Only write if it doesn't exist or is an alpha version (to preserve manually tuned seeds)
        if not output_file.exists() or "alpha" in seed['metadata']['version']:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(seed, f, indent=4, ensure_ascii=False)
            
            success_count += 1
            print(f"  [+] {meta['name']} -> {output_file.name}")
        
    print(f"\n=======================================================")
    print(f"✅ PROCESO FINALIZADO")
    print(f"Asimilados/Actualizados: {success_count} módulos")
    print(f"Errores:                {error_count}")
    print(f"Ubicación:             {OUTPUT_DIR}")
    print(f"=======================================================")

if __name__ == "__main__":
    batch_transcode()
