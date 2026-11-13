import unittest

from importer.detect import detect_backend, detect_frontend
from tests.helpers import TempDirMixin, write, write_json


def pkg(deps=None, dev=None, scripts=None):
    return {"scripts": scripts if scripts is not None else {"build": "x"},
            "dependencies": deps or {}, "devDependencies": dev or {}}


class DetectFrontendTest(TempDirMixin, unittest.TestCase):
    def test_vite_in_frontend_dir(self):
        write_json(self.tmp / "frontend/package.json", pkg({"react": "1"}, {"vite": "1"}))
        f = detect_frontend(self.tmp, "my-app")
        self.assertEqual(f.dir, self.tmp / "frontend")
        self.assertEqual((f.kind, f.output_dir, f.build_args), ("vite", "dist", ["--base=/apps/my-app/"]))
        self.assertIn("React", f.tags)
        self.assertIn("Vite", f.tags)

    def test_astro_at_root(self):
        write_json(self.tmp / "package.json", pkg({"astro": "1"}))
        f = detect_frontend(self.tmp, "s")
        self.assertEqual((f.dir, f.kind, f.output_dir, f.build_args), (self.tmp, "astro", "dist", ["--base", "/apps/s/"]))

    def test_next_with_static_export(self):
        write_json(self.tmp / "web/package.json", pkg({"next": "1"}))
        write(self.tmp / "web/next.config.ts", 'const c = { output: "export", basePath: "/apps/s", trailingSlash: true };')
        f = detect_frontend(self.tmp, "s")
        self.assertEqual((f.kind, f.output_dir, f.build_args), ("next-export", "out", []))

    def test_next_export_without_base_path_is_not_deliverable(self):
        write_json(self.tmp / "web/package.json", pkg({"next": "1"}))
        write(self.tmp / "web/next.config.ts", 'const c = { output: "export" };')
        f = detect_frontend(self.tmp, "s")
        self.assertIsNone(f.kind)
        self.assertIn("basePath", f.reason)

    def test_next_export_without_trailing_slash_is_not_deliverable(self):
        write_json(self.tmp / "web/package.json", pkg({"next": "1"}))
        write(self.tmp / "web/next.config.ts", 'const c = { output: "export", basePath: "/apps/s" };')
        write(self.tmp / "web/package-lock.json", "{}")
        f = detect_frontend(self.tmp, "s")
        self.assertIsNone(f.kind)
        self.assertIn("trailingSlash", f.reason)

    def test_frontend_without_lockfile_is_not_deliverable(self):
        (self.tmp / "frontend").mkdir()
        write_json(self.tmp / "frontend/package.json", pkg({}, {"vite": "1"}))
        f = detect_frontend(self.tmp, "s", require_lockfile=True)
        self.assertIsNone(f.kind)
        self.assertIn("package-lock.json", f.reason)

    def test_vite_meta_frameworks_are_not_deliverable(self):
        for dep in ["@sveltejs/kit", "nuxt", "@remix-run/dev", "@react-router/dev"]:
            with self.subTest(dep=dep):
                write_json(self.tmp / "frontend/package.json", pkg({dep: "1"}, {"vite": "1"}))
                f = detect_frontend(self.tmp, "s")
                self.assertIsNone(f.kind)
                self.assertIn(dep, f.reason)

    def test_astro_server_output_is_not_deliverable(self):
        write_json(self.tmp / "package.json", pkg({"astro": "1"}))
        write(self.tmp / "astro.config.mjs", 'export default defineConfig({ output: "server" });')
        self.assertIsNone(detect_frontend(self.tmp, "s").kind)

    def test_next_without_export_is_not_deliverable(self):
        write_json(self.tmp / "frontend/package.json", pkg({"next": "1"}))
        f = detect_frontend(self.tmp, "s")
        self.assertIsNone(f.kind)
        self.assertIn("output", f.reason)
        self.assertIn("Next.js", f.tags)

    def test_unknown_framework_is_not_deliverable(self):
        write_json(self.tmp / "client/package.json", pkg({"jquery": "1"}))
        f = detect_frontend(self.tmp, "s")
        self.assertIsNone(f.kind)
        self.assertTrue(f.reason)

    def test_no_build_script_means_no_frontend(self):
        write_json(self.tmp / "frontend/package.json", pkg({"vite": "1"}, scripts={}))
        self.assertIsNone(detect_frontend(self.tmp, "s"))

    def test_root_package_without_framework_is_not_frontend(self):
        write_json(self.tmp / "package.json", pkg({"express": "1"}))
        self.assertIsNone(detect_frontend(self.tmp, "s"))


class DetectBackendTest(TempDirMixin, unittest.TestCase):
    def test_python_backend_dir_with_fastapi_tag(self):
        write(self.tmp / "backend/pyproject.toml", '[project]\ndependencies = ["fastapi>=0.1"]\n')
        b = detect_backend(self.tmp, None)
        self.assertEqual((b.dir, b.kind), (self.tmp / "backend", "python"))
        self.assertEqual(b.tags, ["Python", "FastAPI"])

    def test_root_requirements_is_python_backend(self):
        write(self.tmp / "requirements.txt", "flask\n")
        b = detect_backend(self.tmp, None)
        self.assertEqual((b.dir, b.kind), (self.tmp, "python"))
        self.assertIn("Flask", b.tags)

    def test_node_backend_dir(self):
        write_json(self.tmp / "server/package.json", pkg({"express": "1"}, scripts={"start": "node ."}))
        b = detect_backend(self.tmp, None)
        self.assertEqual((b.dir, b.kind), (self.tmp / "server", "node"))
        self.assertIn("Express", b.tags)

    def test_root_express_is_node_backend(self):
        write_json(self.tmp / "package.json", pkg({"express": "1"}, scripts={"start": "node ."}))
        self.assertEqual(detect_backend(self.tmp, None).kind, "node")

    def test_root_package_used_as_frontend_is_not_backend(self):
        write_json(self.tmp / "package.json", pkg({"vite": "1", "express": "1"}))
        f = detect_frontend(self.tmp, "s")
        self.assertIsNone(detect_backend(self.tmp, f))

    def test_none_when_no_backend(self):
        write(self.tmp / "README.md", "# x")
        self.assertIsNone(detect_backend(self.tmp, None))


if __name__ == "__main__":
    unittest.main()
