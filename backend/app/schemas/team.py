from pydantic import BaseModel, ConfigDict


class TeamBase(BaseModel):
    name: str
    short_name: str | None = None
    country: str | None = None
    league_name: str | None = None
    logo_url: str | None = None


class TeamRead(TeamBase):
    id: int
    provider_id: str | None = None

    model_config = ConfigDict(from_attributes=True)
