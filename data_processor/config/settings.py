import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Application settings
APP_NAME = "Core Operations Service"
APP_VERSION = "0.1.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Hardware settings
LIGHT_SENSOR_PIN = int(os.getenv("LIGHT_SENSOR_PIN", "17"))
DHT20_PIN = int(os.getenv("DHT20_PIN", "4"))
SOIL_MOISTURE_PIN = int(os.getenv("SOIL_MOISTURE_PIN", "27"))
WATER_PUMP_PIN = int(os.getenv("WATER_PUMP_PIN", "22"))

# Redis settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Firebase settings
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "")

# Sensor reading settings
READING_INTERVAL_SECONDS = int(os.getenv("READING_INTERVAL_SECONDS", "300"))  # 5 minutes

# Irrigation settings
DEFAULT_IRRIGATION_DURATION = int(os.getenv("DEFAULT_IRRIGATION_DURATION", "60"))  # 60 seconds
SOIL_MOISTURE_THRESHOLD = int(os.getenv("SOIL_MOISTURE_THRESHOLD", "30"))  # 30%

# Adafruit IO settings
ADAFRUIT_IO_USERNAME = os.getenv("ADAFRUIT_IO_USERNAME", "")
ADAFRUIT_IO_KEY = os.getenv("ADAFRUIT_IO_KEY", "")
ADAFRUIT_IO_GROUP = os.getenv("ADAFRUIT_IO_GROUP", "farm-sensors")

# Adafruit feed names
ADAFRUIT_LIGHT_FEED = os.getenv("ADAFRUIT_LIGHT_FEED", "light")
ADAFRUIT_TEMPERATURE_FEED = os.getenv("ADAFRUIT_TEMPERATURE_FEED", "temperature")
ADAFRUIT_HUMIDITY_FEED = os.getenv("ADAFRUIT_HUMIDITY_FEED", "humidity")
ADAFRUIT_SOIL_MOISTURE_FEED = os.getenv("ADAFRUIT_SOIL_MOISTURE_FEED", "soil-moisture")

# Update interval settings
ADAFRUIT_POLL_INTERVAL = int(os.getenv("ADAFRUIT_POLL_INTERVAL", "60"))  # seconds