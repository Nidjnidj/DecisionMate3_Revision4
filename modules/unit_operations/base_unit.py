class BaseUnit:
    def __init__(self, name):
        self.name = name
        self.inputs = {
    "flowrate": 1000,
    "pressure": 5,
    "temperature": 25,
    "composition": {
        "Methane": 0.9,
        "Ethane": 0.1
    }
}

        self.outputs = {}

    def calculate(self):
        raise NotImplementedError("Subclasses must implement the calculate method.")
