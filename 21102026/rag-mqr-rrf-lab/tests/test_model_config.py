import pytest

import llm_client


@pytest.mark.parametrize("kind,default", [("CHAT", "gpt-4o-mini"), ("EMBED", "text-embedding-3-small")])
def test_mode_specific_models_and_legacy_fallback(monkeypatch, kind, default):
    for name in (f"DIRECT_{kind}_MODEL", f"ENTERPRISE_{kind}_MODEL", f"{kind}_MODEL", "OPENAI_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    assert llm_client._model(kind, "direct", default) == default
    monkeypatch.setenv(f"{kind}_MODEL", "legacy-model")
    assert llm_client._model(kind, "direct", default) == "legacy-model"
    monkeypatch.setenv(f"DIRECT_{kind}_MODEL", "direct-model")
    monkeypatch.setenv(f"ENTERPRISE_{kind}_MODEL", "azure/enterprise-model")
    assert llm_client._model(kind, "direct", default) == "direct-model"
    assert llm_client._model(kind, "enterprise", default) == "azure/enterprise-model"
    monkeypatch.setenv(f"DIRECT_{kind}_MODEL", "azure/gateway-model")
    with pytest.raises(RuntimeError, match=f"DIRECT_{kind}_MODEL"):
        llm_client._model(kind, "direct", default)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://custom.example/v1")
    assert llm_client._model(kind, "direct", default) == "azure/gateway-model"
