from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    # Database
    db_dsn: str = "postgresql+asyncpg://billing_user:billing_pass@localhost:5456/billing_db"
    
    # Security
    service_token: str = "gateway-secret-key-2024"
    
    # Service
    service_name: str = "billing-tariffication"
    service_version: str = "1.0.0"
    
    # Kafka
    kafka_bootstrap_servers: str = "kafka:29092"
    
    class Config:
        env_file = ".env"

# Переопределяем DSN для Docker
if os.getenv("DOCKER_ENV"):
    settings = Settings(
        db_dsn="postgresql+asyncpg://billing_user:billing_pass@postgres:5432/billing_db"
    )
else:
    settings = Settings() 