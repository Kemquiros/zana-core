class MockLLM:
    def __init__(self, model_size="small"):
        self.model_size = model_size
        
    def generate(self, prompt):
        return "Respuesta simulada del modelo " + self.model_size

class MockSocket:
    def connect(self, addr):
        return True
