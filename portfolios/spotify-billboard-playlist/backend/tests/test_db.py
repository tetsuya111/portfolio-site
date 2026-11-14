from app.batch.parser import ChartEntry
from app.db import Database


def test_add_source_prunes_oldest():
    db = Database(":memory:", max_sources=3)
    first = db.add_source("https://billboard.mryogaku.com/")
    db.mark_done(first, [ChartEntry(1, "Song", "Artist")])
    ids = [db.add_source("https://billboard.mryogaku.com/") for _ in range(3)]
    assert db.get_source(first) is None
    assert db.tracks(first) == []
    assert all(db.get_source(i) is not None for i in ids)


def test_add_source_keeps_pending_sources():
    db = Database(":memory:", max_sources=2)
    ids = [db.add_source("https://billboard.mryogaku.com/") for _ in range(4)]
    assert db.pending_ids() == ids  # 未処理は上限を超えても消さない
    db.mark_failed(ids[0], "x")
    db.add_source("https://billboard.mryogaku.com/")
    assert db.get_source(ids[0]) is None
    assert db.pending_ids()[0] == ids[1]
