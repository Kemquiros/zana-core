import os
import sys

# Add zana-core to sys.path so it can find zana_steel_core.so
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import zana_steel_core

def test_memory():
    # Initialize Vector Index
    index = zana_steel_core.PyVectorIndex()
    
    # Add documents
    index.add("doc1", [0.1, 0.2, 0.3], '{"source": "test1"}')
    index.add("doc2", [0.9, 0.8, 0.7], '{"source": "test2"}')
    index.add("doc3", [0.1, 0.3, 0.2], '{"source": "test3"}')
    
    # Search
    results = index.search([0.1, 0.25, 0.25], 2)
    print("Search results:", results)
    
    assert len(results) == 2
    assert results[0][0] in ["doc1", "doc3"] # doc1 and doc3 are similar to the query

    # Save and Load
    index.save("test_index.json")
    loaded_index = zana_steel_core.PyVectorIndex.load("test_index.json")
    
    results2 = loaded_index.search([0.9, 0.8, 0.7], 1)
    print("Loaded search results:", results2)
    assert results2[0][0] == "doc2"
    
    print("Memory Engine tests passed!")

if __name__ == "__main__":
    test_memory()