import unittest

from importer.detect import Backend
from importer.mock import Route, extract_routes, write_mock_handlers
from tests.helpers import TempDirMixin, write


class ExtractRoutesTest(TempDirMixin, unittest.TestCase):
    def py(self, text: str, name: str = "app/main.py"):
        write(self.tmp / name, text)
        return extract_routes(Backend(self.tmp, "python"))

    def test_fastapi_decorators(self):
        routes = self.py(
            '@app.get("/api/me")\ndef me(): ...\n'
            '@app.post(\n    "/api/playlists",\n    response_model=X,\n)\ndef p(): ...\n'
            "@router.delete('/items/{item_id}')\ndef d(): ...\n"
            '@app.get("/files/{file_path:path}")\ndef f(): ...\n')
        self.assertEqual(routes, [Route("GET", "/api/me"), Route("POST", "/api/playlists"),
                                  Route("DELETE", "/items/:item_id"), Route("GET", "/files/:file_path")])

    def test_flask_route(self):
        routes = self.py('@app.route("/x/<int:id>", methods=["GET", "POST"])\ndef x(): ...\n'
                         '@bp.route("/y/<name>")\ndef y(): ...\n')
        self.assertEqual(routes, [Route("GET", "/x/:id"), Route("POST", "/x/:id"), Route("GET", "/y/:name")])

    def test_flask_route_methods_as_tuple(self):
        routes = self.py('@app.route("/login", methods=("GET", "POST"))\ndef login(): ...\n'
                         '@app.route(\n    "/multi",\n    methods=[\n        "PUT",\n    ],\n)\ndef m(): ...\n')
        self.assertEqual(routes, [Route("GET", "/login"), Route("POST", "/login"), Route("PUT", "/multi")])

    def test_flask_stacked_routes_keep_their_own_methods(self):
        routes = self.py('@app.route("/a")\n@app.route("/b", methods=["POST"])\ndef f(): ...\n')
        self.assertEqual(routes, [Route("GET", "/a"), Route("POST", "/b")])

    def test_node_routes(self):
        write(self.tmp / "src/server.ts", "router.post('/api/x', h)\napp.get(`/api/items/:id`, h)\n"
                                          'app.put("/api/z", h)\n')
        routes = extract_routes(Backend(self.tmp, "node"))
        self.assertEqual(routes, [Route("POST", "/api/x"), Route("GET", "/api/items/:id"), Route("PUT", "/api/z")])

    def test_ignores_tests_and_duplicates(self):
        write(self.tmp / "tests/test_api.py", '@app.get("/t1")\n')
        write(self.tmp / "app/test_main.py", '@app.get("/t2")\n')
        write(self.tmp / "src/a.test.js", 'app.get("/t3", h)\n')
        write(self.tmp / "src/a.spec.ts", 'app.get("/t4", h)\n')
        routes = self.py('@app.get("/a")\n@app.get("/a")\n')
        self.assertEqual(routes, [Route("GET", "/a")])

    def test_node_ignores_http_client_calls_and_excluded_dirs(self):
        write(self.tmp / "server.js", 'app.get("/a", h)\naxios.get("/b")\nhttp.post("/c")\n')
        write(self.tmp / "frontend/src/api.js", 'app.get("/front", h)\n')
        routes = extract_routes(Backend(self.tmp, "node"), exclude=[self.tmp / "frontend"])
        self.assertEqual(routes, [Route("GET", "/a")])

    def test_python_backend_ignores_js(self):
        write(self.tmp / "static/app.js", 'app.get("/js", h)\n')
        self.assertEqual(self.py('@app.get("/a")\n'), [Route("GET", "/a")])


class WriteMockHandlersTest(TempDirMixin, unittest.TestCase):
    def test_writes_a_handler_per_route(self):
        path, warnings = write_mock_handlers(self.tmp, [Route("GET", "/api/me"), Route("POST", "/api/items/:id")])
        self.assertEqual(path, self.tmp / "mock/handlers.js")
        self.assertEqual(warnings, [])
        text = path.read_text(encoding="utf-8")
        self.assertIn('portfolioMock.handle("GET", "/api/me", (req) => {', text)
        self.assertIn('portfolioMock.handle("POST", "/api/items/:id", (req) => {', text)
        self.assertEqual(text.count("TODO"), 2)

    def test_writes_example_only_and_warns_without_routes(self):
        path, warnings = write_mock_handlers(self.tmp, [])
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("\nportfolioMock.handle(", text)
        self.assertIn("// portfolioMock.handle(", text)
        self.assertEqual(len(warnings), 1)
        self.assertIn("ルート", warnings[0])

    def test_skips_routes_without_a_fixed_segment(self):
        path, warnings = write_mock_handlers(self.tmp, [Route("GET", "/"), Route("GET", "/:slug"), Route("GET", "/a")])
        text = path.read_text(encoding="utf-8")
        self.assertIn('"/a"', text)
        self.assertNotIn('"/"', text)
        self.assertNotIn('"/:slug"', text)
        self.assertEqual(len(warnings), 1)
        self.assertIn("GET /:slug", warnings[0])

    def test_does_not_overwrite(self):
        write(self.tmp / "mock/handlers.js", "// mine")
        path, warnings = write_mock_handlers(self.tmp, [Route("GET", "/a")])
        self.assertEqual(path, self.tmp / "mock/handlers.js")
        self.assertEqual(path.read_text(encoding="utf-8"), "// mine")
        self.assertEqual(len(warnings), 1)


if __name__ == "__main__":
    unittest.main()
