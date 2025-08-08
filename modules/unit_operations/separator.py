from modules.unit_operations.base_unit import BaseUnit

class Separator(BaseUnit):
    def __init__(self, name):
        super().__init__(name)
        self.split_ratio = 0.5  # default 50% flow to each outlet

    def calculate(self):
        flow_in = self.inputs["flowrate"]
        pressure = self.inputs["pressure"]
        temperature = self.inputs["temperature"]
        composition = self.inputs["composition"]

        # Use a simple split ratio (e.g., gas/liquid separator logic)
        flow1 = flow_in * self.split_ratio
        flow2 = flow_in * (1 - self.split_ratio)

        self.outputs = {
            "Outlet1": {
                "flowrate": flow1,
                "pressure": pressure,
                "temperature": temperature,
                "composition": composition
            },
            "Outlet2": {
                "flowrate": flow2,
                "pressure": pressure,
                "temperature": temperature,
                "composition": composition
            }
        }
