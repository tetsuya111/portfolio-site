"""API 仕様（OpenAPI）に設計どおりのエンドポイントが載っていること。"""

EXPECTED = {
    ("get", "/health"),
    ("post", "/auth/login"),
    ("post", "/auth/register"),
    ("get", "/users/me"),
    ("get", "/users"),
    ("get", "/products"),
    ("post", "/products"),
    ("get", "/products/{product_id}"),
    ("put", "/products/{product_id}"),
    ("delete", "/products/{product_id}"),
    ("post", "/inventory/in"),
    ("post", "/inventory/out"),
    ("get", "/inventory/history"),
    ("get", "/inventory/summary"),
}


def test_openapi_lists_all_endpoints(client):
    spec = client.get("/openapi.json").json()
    actual = {(method, path) for path, ops in spec["paths"].items() for method in ops}
    assert actual == EXPECTED


def test_protected_endpoints_declare_bearer_auth(client):
    spec = client.get("/openapi.json").json()
    public = {("get", "/health"), ("post", "/auth/login")}
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            if (method, path) in public:
                continue
            assert op.get("security"), f"{method.upper()} {path} に認証の定義がない"
