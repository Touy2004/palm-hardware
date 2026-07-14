import time

class ThermalService:
    def __init__(self):
        import board
        import busio as io
        import adafruit_mlx90614

        i2c = io.I2C(board.SCL, board.SDA, frequency=100000)
        self.sensor = adafruit_mlx90614.MLX90614(i2c)
        print("Thermal sensor (MLX90614) initialized successfully.")

    def read_max_temp(self) -> float:
        # For the MLX90614, the object_temperature is the target's temp
        return self.sensor.object_temperature
