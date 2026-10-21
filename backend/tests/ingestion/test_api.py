import httpx
import pytest

from app.ingestion import data_taipei
from app.ingestion.normalize import normalize_work_bureau


URL = "https://data.taipei/api/v1/dataset/a064da04-bfe4-4677-a04e-fe95eeb81fa3?scope=resourceAquire"


def row(index):
    return {"_id": index, "_importdate": {"date": "2026-05-11 12:03:50"},
            "機關名稱": "臺北市政府工務局", "標案案號": f"A-{index}", "標案名稱": "道路工程",
            "標的分類": "工程類", "總決標金額": "1,234"}


def test_fetches_all_pages_and_keeps_resource_id_and_stable_checksum():
    offsets = []

    def handler(request):
        offset = int(request.url.params["offset"])
        offsets.append(offset)
        assert request.url.params["scope"] == "resourceAquire"
        assert request.url.params["sort"] == "_id"
        return httpx.Response(200, json={"result": {"count": 3, "offset": offset,
                              "results": [row(i) for i in range(offset, min(offset + 2, 3))]}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = data_taipei.fetch_api(URL, client=client, page_size=2)
        again = data_taipei.fetch_api(URL, client=client, page_size=2)
    assert offsets == [0, 2, 0, 2]
    assert len(result.rows) == 3
    assert result.resource_id == "a064da04-bfe4-4677-a04e-fe95eeb81fa3"
    assert result.checksum == again.checksum
    normalized = normalize_work_bureau(result.rows[0], source_period="2026-05", source_url=URL)
    assert normalized.award_amount == 1234
    assert normalized.announcement_date is None
    assert normalized.source_url == URL


@pytest.mark.parametrize("fault", ["empty_page", "repeated_row", "count_changed", "wrong_offset"])
def test_incomplete_or_changing_snapshots_are_rejected(fault):
    def handler(request):
        offset = int(request.url.params["offset"])
        data = {"count": 2, "offset": offset, "results": [row(offset)]}
        if offset:
            if fault == "empty_page": data["results"] = []
            if fault == "repeated_row": data["results"] = [row(0)]
            if fault == "count_changed": data["count"] = 3
            if fault == "wrong_offset": data["offset"] = 0
        return httpx.Response(200, json={"result": data})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError):
            data_taipei.fetch_api(URL, client=client, page_size=1)


@pytest.mark.parametrize("payload", [{}, {"result": {"count": "invalid", "results": []}},
                                    {"result": {"count": 1, "results": ["bad row"]}}])
def test_malformed_api_data_is_rejected(payload):
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))) as client:
        with pytest.raises(ValueError):
            data_taipei.fetch_api(URL, client=client)


def test_http_error_propagates_and_empty_dataset_is_valid():
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503))) as client:
        with pytest.raises(httpx.HTTPStatusError):
            data_taipei.fetch_api(URL, client=client)
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={
            "result": {"count": 0, "offset": 0, "results": []}}))) as client:
        assert data_taipei.fetch_api(URL, client=client).rows == []


def test_redirect_cannot_downgrade_https_or_leave_the_official_endpoint():
    def handler(request):
        if request.url.scheme == "https":
            return httpx.Response(302, headers={"Location": "http://data.taipei/plain"})
        return httpx.Response(200, json={"result": {"count": 0, "offset": 0, "results": []}})
    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        with pytest.raises(httpx.HTTPStatusError):
            data_taipei.fetch_api(URL, client=client)


def test_api_cli_dry_run_does_not_connect_to_database(monkeypatch, capsys):
    import sys
    from types import SimpleNamespace
    from app import cli
    monkeypatch.setattr(sys, "argv", ["cli", "sync-cases", "--source", "work-bureau", "--resource-url", URL,
                                    "--format", "api", "--period", "2026-05", "--dry-run"])
    monkeypatch.setattr(cli, "fetch_api", lambda url: SimpleNamespace(rows=[row(1)], checksum="abc", resource_id="test"), raising=False)
    cli.main()
    output = capsys.readouterr().out
    assert "records=1" in output
    assert "missing_award_dates=1" in output
