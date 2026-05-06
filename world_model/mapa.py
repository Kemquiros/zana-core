import numpy as np


# Stub dependencies
def dilate(mapa, rows, cols, factor): return mapa
def erode(mapa, rows, cols, factor): return mapa

class DataMap:
    def __init__(self):
        self.promMovimiento = 10
        self.tiles = {i: {"n": 1} for i in range(1, 16)}

class Castillo:
    def __init__(self, fila, columna):
        self.fila = fila
        self.columna = columna
        self.propietario = None

class Templo:
    def __init__(self, fila, columna):
        self.fila = fila
        self.columna = columna

class Taberna:
    def __init__(self, fila, columna):
        self.fila = fila
        self.columna = columna

class Mapa:
    data = DataMap()
    traslacionCapa = {1:"prado",2:"oceano",3:"rio",4:"camino",5:"bosque",6:"montana",7:"nieve",8:"taberna",9:"castillo",10:"aldea",11:"ciudad",12:"templo",13:"portal",14:"montana-nieve",15:"montana-sagrada"}

    def __init__(self, numeroJugadores):
        self.nroJugadores = numeroJugadores
        self.nroFilas = self.nroJugadores * self.data.promMovimiento
        self.nroColumnas = self.nroJugadores * self.data.promMovimiento
        self.mapa1 = np.ones((self.nroFilas, self.nroColumnas))
        self.mapa2 = np.zeros((self.nroFilas, self.nroColumnas))
        self.mapa3 = np.zeros((self.nroFilas, self.nroColumnas))
        self.castillos = {}
        self.templos = {}
        self.tabernas = {}

    def crearMapa(self):
        # Simplified version for now
        pass

    def puntoPerteneceMapa(self, x, y):
        return 0 <= x < self.nroColumnas and 0 <= y < self.nroFilas
