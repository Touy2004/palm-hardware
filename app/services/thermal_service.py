import time

class ThermalService:
    def __init__(self):
        self.sensor = None
        self.mock_mode = False
        self.frame = [0] * 768
        
        try:
            import board
            import busio
            import adafruit_mlx90640

            i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
            self.sensor = adafruit_mlx90640.MLX90640(i2c)
            self.sensor.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
            print("Thermal sensor initialized successfully.")
        except Exception as e:
            print(f"Warning: Could not initialize thermal sensor: {e}")
            print("Falling back to mock thermal mode.")
            self.mock_mode = True

    def read_max_temp(self) -> float:
        if self.mock_mode:
            # Mock mode returns a safe low temperature
            return 25.0

        try:
            self.sensor.getFrame(self.frame)
            # Filter out any weird anomalies or math errors that occasionally happen
            valid_temps = [t for t in self.frame if not (isinstance(t, float) and (t != t or t == float('inf') or t == float('-inf')))]
            if valid_temps:
                return max(valid_temps)
            return 0.0
        except ValueError:
            # Sensor reading error (ValueError is common in I2C errors for mlx)
            return 0.0
        except Exception as e:
            print(f"Error reading thermal frame: {e}")
            return 0.0
