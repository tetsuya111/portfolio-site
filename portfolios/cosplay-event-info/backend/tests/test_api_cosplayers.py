import pytest

from catalog.models import Cosplayer, FetchedPage

pytestmark = pytest.mark.django_db


def names(response):
    return [c["name"] for c in response.json()["results"]]


def test_cosplayers_are_ordered_by_name(client):
    Cosplayer.objects.create(name="さくら")
    Cosplayer.objects.create(name="あおい")

    assert names(client.get("/api/cosplayers/")) == ["あおい", "さくら"]


def test_cosplayer_keyword_matches_name_description_and_career(client):
    Cosplayer.objects.create(name="甲冑の人")
    Cosplayer.objects.create(name="B", description="甲冑の造形が得意")
    Cosplayer.objects.create(name="C", career="甲冑で受賞")
    Cosplayer.objects.create(name="D", description="和装")

    assert sorted(names(client.get("/api/cosplayers/", {"q": "甲冑"}))) == ["B", "C", "甲冑の人"]


def test_cosplayer_detail(client):
    person = Cosplayer.objects.create(
        name="うえ",
        sns_links=["https://x.com/ue", "javascript:alert(1)"],
        career="経歴",
        description="説明",
        notes="備考",
        source_url="https://ja.wikipedia.org/wiki/ue",
    )
    person.sources.add(
        FetchedPage.objects.create(
            url="https://ja.wikipedia.org/wiki/ue", kind="cosplayer", status_code=200
        )
    )

    body = client.get(f"/api/cosplayers/{person.id}/").json()

    assert body["name"] == "うえ"
    assert body["sns_links"] == ["https://x.com/ue"]
    assert body["career"] == "経歴"
    assert body["description"] == "説明"
    assert body["notes"] == "備考"
    assert body["source_url"] == "https://ja.wikipedia.org/wiki/ue"
    assert [s["url"] for s in body["sources"]] == ["https://ja.wikipedia.org/wiki/ue"]


def test_cosplayer_list_has_no_sources(client):
    Cosplayer.objects.create(name="x")

    assert "sources" not in client.get("/api/cosplayers/").json()["results"][0]
