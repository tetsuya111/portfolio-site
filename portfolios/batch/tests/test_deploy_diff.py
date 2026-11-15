import hashlib
import tempfile
import unittest
from pathlib import Path

from deploy_diff import deploy


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


class FakeS3:
    def __init__(self, objects):
        self.objects = dict(objects)  # key -> bytes
        self.puts, self.deletes, self.list_prefixes = [], [], []

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        s3 = self

        class P:
            def paginate(self, Bucket, Prefix=""):
                s3.list_prefixes.append(Prefix)
                items = [{"Key": k, "ETag": f'"{md5(v)}"'} for k, v in s3.objects.items() if k.startswith(Prefix)]
                yield {"Contents": items[:1]}
                yield {"Contents": items[1:]}

        return P()

    def put_object(self, **kw):
        kw["Body"] = kw["Body"].read()
        self.puts.append(kw)

    def delete_objects(self, **kw):
        self.deletes.append(kw)


class FakeCf:
    def __init__(self):
        self.calls = []

    def create_invalidation(self, **kw):
        self.calls.append(kw)


def make_dist(d, files):
    for rel, content in files.items():
        p = Path(d, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)


class DeployTest(unittest.TestCase):
    def run_deploy(self, files, remote, prefix="", distribution_id="E123", delete_removed=False, dry_run=False):
        s3, cf = FakeS3(remote), FakeCf()
        with tempfile.TemporaryDirectory() as d:
            make_dist(d, files)
            r = deploy(s3, cf, dist=Path(d), bucket="b", prefix=prefix, distribution_id=distribution_id,
                       delete_removed=delete_removed, dry_run=dry_run)
        return r, s3, cf

    def test_uploads_only_changed_files(self):
        files = {"index.html": b"same", "it-news/a/index.html": b"new", "_astro/x.css": b"css"}
        r, s3, cf = self.run_deploy(files, {"index.html": b"same", "_astro/x.css": b"old"})
        self.assertEqual(sorted(p["Key"] for p in s3.puts), ["_astro/x.css", "it-news/a/index.html"])
        page = next(p for p in s3.puts if p["Key"] == "it-news/a/index.html")
        self.assertEqual(page["ContentType"], "text/html; charset=utf-8")
        self.assertEqual(page["CacheControl"], "public, max-age=0, must-revalidate")
        css = next(p for p in s3.puts if p["Key"] == "_astro/x.css")
        self.assertEqual(css["CacheControl"], "public, max-age=31536000, immutable")
        self.assertEqual(sorted(cf.calls[0]["InvalidationBatch"]["Paths"]["Items"]), ["/it-news/a/", "/it-news/a/index.html"])
        self.assertEqual(r["changed"], 2)

    def test_prefix_applies_to_keys_but_not_paths(self):
        r, s3, cf = self.run_deploy({"index.html": b"x"}, {"preview/other.txt": b"y"}, prefix="preview")
        self.assertEqual(s3.list_prefixes, ["preview/"])
        self.assertEqual(s3.puts[0]["Key"], "preview/index.html")
        self.assertEqual(sorted(cf.calls[0]["InvalidationBatch"]["Paths"]["Items"]), ["/", "/index.html"])
        self.assertEqual(s3.deletes, [])

    def test_url_encodes_invalidation_paths(self):
        _, _, cf = self.run_deploy({"articles/日本語 a/index.html": b"x"}, {})
        self.assertEqual(
            sorted(cf.calls[0]["InvalidationBatch"]["Paths"]["Items"]),
            ["/articles/%E6%97%A5%E6%9C%AC%E8%AA%9E%20a/", "/articles/%E6%97%A5%E6%9C%AC%E8%AA%9E%20a/index.html"],
        )

    def test_logs_only_the_count_of_stale_objects(self):
        s3, cf, logs = FakeS3({f"apps/x/{i}.js": b"y" for i in range(50)}), FakeCf(), []
        with tempfile.TemporaryDirectory() as d:
            make_dist(d, {"a.html": b"x"})
            deploy(s3, cf, dist=Path(d), bucket="b", prefix="", distribution_id="", delete_removed=False, dry_run=False,
                   log=logs.append)
        self.assertFalse(any(line.startswith("stale") and "apps/x/" in line for line in logs))
        self.assertTrue(any("50" in line for line in logs))

    def test_collapses_many_paths(self):
        files = {f"p{i}/index.html": b"x" for i in range(60)}
        _, _, cf = self.run_deploy(files, {})
        self.assertEqual(cf.calls[0]["InvalidationBatch"]["Paths"], {"Quantity": 1, "Items": ["/*"]})

    def test_does_not_delete_by_default(self):
        r, s3, _ = self.run_deploy({"a.html": b"x"}, {"a.html": b"x", "apps/app/index.html": b"y"})
        self.assertEqual(s3.deletes, [])
        self.assertEqual(r["removed"], 1)

    def test_deletes_when_asked(self):
        _, s3, cf = self.run_deploy({"a.html": b"x"}, {"a.html": b"x", "old/index.html": b"y"}, delete_removed=True)
        self.assertEqual(s3.deletes[0]["Delete"]["Objects"], [{"Key": "old/index.html"}])
        self.assertEqual(sorted(cf.calls[0]["InvalidationBatch"]["Paths"]["Items"]), ["/old/", "/old/index.html"])

    def test_no_invalidation_without_distribution_or_changes(self):
        _, _, cf = self.run_deploy({"a.html": b"x"}, {}, distribution_id="")
        self.assertEqual(cf.calls, [])
        _, _, cf = self.run_deploy({"a.html": b"x"}, {"a.html": b"x"})
        self.assertEqual(cf.calls, [])

    def test_dry_run_sends_nothing(self):
        r, s3, cf = self.run_deploy({"a.html": b"x"}, {}, dry_run=True)
        self.assertEqual((s3.puts, cf.calls, r["changed"]), ([], [], 1))


if __name__ == "__main__":
    unittest.main()
