from src.api.schemas.schemas import ListLinksUpdate


def test_json_to_dto():
    data = {"links": [{"id": 5, "url": "http://ex", "description": "desc", "tg_chat_id": 1}]}
    dto = ListLinksUpdate(**data)
    assert dto.links[0].url == "http://ex"
