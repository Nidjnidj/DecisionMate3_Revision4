from .base_unit import BaseUnit

class Pump(BaseUnit):
    def calculate(self):
        self.outputs["flowrate"] = self.inputs["flowrate"]
        self.outputs["temperature"] = self.inputs["temperature"]
        self.outputs["pressure"] = self.inputs["pressure"] + 5  # Adds 5 bar
        self.outputs["composition"] = self.inputs["composition"]
        self.outputs["composition"] = self.inputs["composition"]

