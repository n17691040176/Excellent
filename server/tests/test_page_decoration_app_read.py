from types import SimpleNamespace

from app.services.page_decoration_service import PageDecorationService


def test_anonymous_app_read_uses_only_global_decoration(monkeypatch):
    calls = []
    global_record = SimpleNamespace(id=7, team_id=None, payload={}, updated_at=None)

    def query_record(_db, team_id):
        calls.append(team_id)
        return global_record

    monkeypatch.setattr(PageDecorationService, '_query_record', staticmethod(query_record))

    result = PageDecorationService.get_mobile_uni_home_for_app(object(), None)

    assert calls == [None]
    assert result['id'] == 7
    assert result['team_id'] is None


def test_logged_in_app_read_prefers_team_decoration(monkeypatch):
    calls = []
    team_record = SimpleNamespace(id=11, team_id=42, payload={}, updated_at=None)

    def query_record(_db, team_id):
        calls.append(team_id)
        return team_record if team_id == 42 else None

    monkeypatch.setattr(PageDecorationService, '_query_record', staticmethod(query_record))

    result = PageDecorationService.get_mobile_uni_home_for_app(object(), SimpleNamespace(team_id=42))

    assert calls == [42]
    assert result['id'] == 11
    assert result['team_id'] == 42


def test_logged_in_app_read_falls_back_to_global_decoration(monkeypatch):
    calls = []
    global_record = SimpleNamespace(id=13, team_id=None, payload={}, updated_at=None)

    def query_record(_db, team_id):
        calls.append(team_id)
        return global_record if team_id is None else None

    monkeypatch.setattr(PageDecorationService, '_query_record', staticmethod(query_record))

    result = PageDecorationService.get_mobile_uni_home_for_app(object(), SimpleNamespace(team_id=42))

    assert calls == [42, None]
    assert result['id'] == 13
    assert result['team_id'] is None
