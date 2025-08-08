from modules.unit_operations.base_unit import BaseUnit

class Pipe(BaseUnit):
    def calculate(self):
        # Simulates pressure drop through a pipe (simplified)
        flow = self.inputs["flowrate"]
        pressure = self.inputs["pressure"]
        temp = self.inputs["temperature"]

        drop = 0.01 * flow / 100  # Pressure drop: simplified rule
        self.outputs["flowrate"] = flow
        self.outputs["pressure"] = pressure - drop
        self.outputs["temperature"] = temp
        self.outputs["composition"] = self.inputs["composition"]
        self.outputs["composition"] = self.inputs["composition"]
