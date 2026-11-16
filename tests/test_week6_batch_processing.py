import json
from types import SimpleNamespace

import pytest

from scripts import process_week6_listings as batch


class FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.closed = False
        self.executed = None

    def execute(self, query, params):
        self.executed = (query, params)

    def fetchmany(self, size):
        result, self.rows = self.rows[:size], self.rows[size:]
        return result

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)
        self.closed = False

    def cursor(self, *, dictionary):
        assert dictionary is True
        return self.cursor_instance

    def close(self):
        self.closed = True


class Extractor:
    def extract_signals(self, listing):
        if listing["L_ListingID"] == "bad":
            raise RuntimeError("bad listing")
        return {"listing_id": str(listing["L_ListingID"]), "entities": {}, "flags": {}, "keywords": {}, "amenities": []}


def test_batch_processing_streams_jsonl_and_handles_missing_remarks_and_errors(tmp_path, monkeypatch):
    rows = [
        {"L_ListingID": "one", "L_Remarks": None, "L_City": "A"},
        {"L_ListingID": "bad", "L_Remarks": "text", "L_City": "B"},
        {"L_ListingID": "three", "L_Remarks": "remarks", "L_City": "C"},
    ]
    connection = FakeConnection(rows)
    monkeypatch.setattr(batch, "connection_settings", lambda args: {"host": "mock"})
    args = SimpleNamespace(limit=3, batch_size=2, output=tmp_path / "signals.jsonl")
    stats = batch.process_listings(args, extractor=Extractor(), connect=lambda **kw: connection)

    records = [json.loads(line) for line in args.output.read_text(encoding="utf-8").splitlines()]
    assert stats == {"processed": 3, "errors": 1, "missing_remarks": 1}
    assert [record["listing_id"] for record in records] == ["one", "bad", "three"]
    assert records[0]["remarks"] == ""
    assert records[0]["source_fields"] == {"L_City": "A"}
    assert records[0]["signals"]["listing_id"] == "one"
    assert records[1]["error"] == "RuntimeError: bad listing"
    assert connection.cursor_instance.executed[1] == (3,)
    assert connection.cursor_instance.closed and connection.closed
    assert not list(tmp_path.glob("*.tmp"))


def test_batch_processing_limit_is_optional_and_output_replaces_atomically(tmp_path, monkeypatch):
    connection = FakeConnection([])
    monkeypatch.setattr(batch, "connection_settings", lambda args: {})
    output = tmp_path / "signals.jsonl"
    output.write_text("previous complete file\n", encoding="utf-8")
    args = SimpleNamespace(limit=None, batch_size=4, output=output)
    batch.process_listings(args, extractor=Extractor(), connect=lambda **kw: connection)
    query, params = connection.cursor_instance.executed
    assert "LIMIT" not in query
    assert params == ()
    assert output.read_text(encoding="utf-8") == ""


def test_batch_processing_failure_keeps_previous_output_and_cleans_temp_file(tmp_path, monkeypatch):
    connection = FakeConnection([])
    monkeypatch.setattr(batch, "connection_settings", lambda args: {})
    output = tmp_path / "signals.jsonl"
    output.write_text("complete previous output\n", encoding="utf-8")

    class FailingCursor(FakeCursor):
        def execute(self, query, params):
            raise RuntimeError("database query failed")

    connection.cursor_instance = FailingCursor([])
    args = SimpleNamespace(limit=1, batch_size=2, output=output)
    with pytest.raises(RuntimeError, match="database query failed"):
        batch.process_listings(args, extractor=Extractor(), connect=lambda **kw: connection)
    assert output.read_text(encoding="utf-8") == "complete previous output\n"
    assert not list(tmp_path.glob("*.tmp"))
    assert connection.closed


@pytest.mark.parametrize("limit,batch_size", [(0, 10), (None, 0)])
def test_batch_processing_rejects_nonpositive_options(tmp_path, limit, batch_size):
    args = SimpleNamespace(limit=limit, batch_size=batch_size, output=tmp_path / "out.jsonl")
    with pytest.raises(ValueError):
        batch.process_listings(args, connect=lambda **kw: pytest.fail("must validate before connecting"))
