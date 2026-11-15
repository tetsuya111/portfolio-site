"""テスト用の偽の HTTP POST（Perplexity の応答を返す）。"""
import json


def response(content, search_results=None, citations=None, status=200):
    body = {"choices": [{"message": {"content": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)}}]}
    if search_results is not None:
        body["search_results"] = search_results
    if citations is not None:
        body["citations"] = citations
    return status, json.dumps(body, ensure_ascii=False)


class FakePost:
    """呼ばれた順に responses を返し、送られた内容を calls に残す。"""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append({"url": url, "headers": headers, "body": json.loads(body), "timeout": timeout})
        if not self.responses:
            raise AssertionError("想定より多く呼ばれました")
        return self.responses.pop(0)
