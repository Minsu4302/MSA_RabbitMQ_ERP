from pydantic_settings import BaseSettings  # pydantic-settings에서 BaseSettings를 임포트

class Settings(BaseSettings):
    # DB URL 환경 변수 관리
    SQLALCHEMY_DATABASE_URL: str = "mysql+asyncmy://erpuser:erppassword@mysql:3306/erp"

    class Config:
        env_file = ".env"  # .env 파일을 통해 환경 변수 관리

# settings 객체를 생성하여 FastAPI에서 사용
settings = Settings()
