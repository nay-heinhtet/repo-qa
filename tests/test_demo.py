import pytest
from fastapi import HTTPException

from repo_qa import api


def test_the_demo_stops_at_its_daily_cap(monkeypatch):
    monkeypatch.setattr(api, "ASKS_PER_DAY", 2)
    monkeypatch.setattr(api, "asks_today", {"day": None, "count": 0})
    api.check_rate_limit("1.1.1.1")
    api.check_rate_limit("2.2.2.2")
    with pytest.raises(HTTPException) as refused:
        api.check_rate_limit("3.3.3.3")  # a new visitor too: the cap is for everyone together
    assert refused.value.status_code == 429
