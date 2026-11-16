from app.batch.parser import ChartEntry
from app.db import Database

URL = "https://billboard.mryogaku.com/"


def test_add_source_prunes_oldest_processed():
    db = Database(":memory:", max_sources=2)
    done = []
    for i in range(3):
        source_id = db.add_source(URL)
        db.mark_done(source_id, [ChartEntry(1, f"Song{i}", "Artist")])
        done.append(source_id)
    db.add_source(URL)  # 処理済みが3件 > 上限2件なので最古の1件を削除する
    assert db.get_source(done[0]) is None
    assert db.tracks(done[0]) == []
    assert db.get_source(done[1]) is not None
    assert db.get_source(done[2]) is not None


def test_add_source_keeps_pending_sources():
    db = Database(":memory:", max_sources=2)
    ids = [db.add_source(URL) for _ in range(4)]
    assert db.pending_ids() == ids  # 未処理は上限を超えても消さない
    for source_id in ids[:3]:
        db.mark_failed(source_id, "x")
    new_id = db.add_source(URL)
    assert db.get_source(ids[0]) is None
    assert db.pending_ids() == [ids[3], new_id]


def test_pending_rows_do_not_push_out_processed_rows():
    db = Database(":memory:", max_sources=2)
    done = db.add_source("https://billboard.mryogaku.com/")
    db.mark_done(done, [ChartEntry(1, "Song", "Artist")])
    for _ in range(3):
        db.add_source("https://billboard.mryogaku.com/")  # 未処理のまま
    assert db.get_source(done) is not None
    assert db.tracks(done) == [ChartEntry(1, "Song", "Artist")]
