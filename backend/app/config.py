from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RWD TrustChain API"
    api_prefix: str = "/api/v1"

    auth_mode: str = "dev"  # "dev" or "keycloak"
    demo_default_user: str = "steward_mateo"

    keycloak_server_url: str = ""
    keycloak_realm: str = ""
    keycloak_client_id: str = ""
    keycloak_jwks_url: str = ""

    consent_required_for_patient_write: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @computed_field
    @property
    def resolved_jwks_url(self) -> str:
        if self.keycloak_jwks_url:
            return self.keycloak_jwks_url
        if self.keycloak_server_url and self.keycloak_realm:
            base = self.keycloak_server_url.rstrip("/")
            return f"{base}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"
        return ""


settings = Settings()