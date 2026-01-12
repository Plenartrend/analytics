from dotenv import find_dotenv, load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(find_dotenv())


class Settings(BaseSettings):
    # Kafka
    KAFKA_BROKER: str
    TOPIC: str

    # Database
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_HOST_NAME: str
    DATABASE_PORT: int
    DATABASE_NAME: str
    # Settings for the logger
    LOGGER_DEFAULT_LOG_LEVEL: int = 20

    LOGGER_STD_OUT_ENABLE_LOGGING: bool = True
    LOGGER_STD_OUT_LOG_LEVEL: int = 20

    LOGGER_FILE_ENABLE_LOGGING: bool = True
    LOGGER_FILE_LOG_PATH: str = "logs"
    LOGGER_FILE_LOG_LEVEL: int = 20
    LOGGER_FILE_BYTE_SIZE: int = 1000000
    LOGGER_FILE_COMPRESSION: bool = False

    LOGGER_HTTP_ENABLE_LOGGING: bool = True
    LOGGER_HTTP_LOG_LEVEL: int = 30

    DEEPSEEK_API_KEY: str

    model_config = SettingsConfigDict(case_sensitive=False)


settings = Settings()  # noqa
