import pytest

from app.services import player_enrichment as enrichment


@pytest.mark.asyncio
async def test_dynamic_team_resolution_exact_match(monkeypatch):
    enrichment._TEAM_CACHE.clear()

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"teams": [
                {"strTeam": "Manchester United", "strSport": "Soccer", "idTeam": "133612"},
                {"strTeam": "Manchester United Women", "strSport": "Soccer", "idTeam": "999999"},
            ]}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params):
            assert params["t"] == "Manchester United"
            return Response()

    monkeypatch.setattr(enrichment.httpx, "AsyncClient", lambda **kwargs: Client())
    result = await enrichment._resolve_team_id({"name": "Manchester United"})
    assert result == 133612
    assert await enrichment._resolve_team_id({"name": "Manchester United"}) == result


@pytest.mark.asyncio
async def test_dynamic_team_resolution_rejects_ambiguous_results(monkeypatch):
    enrichment._TEAM_CACHE.clear()

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"teams": [
                {"strTeam": "Example FC", "strSport": "Soccer", "idTeam": "123"},
                {"strTeam": "Example FC", "strSport": "Soccer", "idTeam": "456"},
            ]}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params):
            return Response()

    monkeypatch.setattr(enrichment.httpx, "AsyncClient", lambda **kwargs: Client())
    assert await enrichment._resolve_team_id({"name": "Example FC"}) is None


def test_player_match_rejects_different_birth_date():
    player = {"name": "Alex Example", "date_of_birth": "2000-01-01"}
    candidate = {"strPlayer": "Alex Example", "dateBorn": "1999-01-01"}
    assert enrichment._match(player, [candidate]) is None
