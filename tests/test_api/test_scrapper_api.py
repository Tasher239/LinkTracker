from http import HTTPStatus
from fastapi.testclient import TestClient


def test_register_user(client: TestClient) -> None:
    tg_chat_id = 12345
    response = client.post(f"/tg-chat/{tg_chat_id}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"message": "Чат зарегистрирован"}


def test_delete_chat(client: TestClient) -> None:
    tg_chat_id = 12345
    # Регистрируем пользователя, если ещё не зарегистрирован
    client.post(f"/tg-chat/{tg_chat_id}")
    response = client.delete(f"/tg-chat/{tg_chat_id}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"message": "Чат удален"}


def test_delete_chat_not_exist(client: TestClient) -> None:
    response = client.delete("/tg-chat/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_links(client: TestClient) -> None:
    tg_chat_id = 12345
    client.post(f"/tg-chat/{tg_chat_id}")
    response = client.get("/links", headers={"tg-chat-id": str(tg_chat_id)})
    assert response.status_code == HTTPStatus.OK
    assert "links" in response.json()


def test_add_link(client: TestClient) -> None:
    tg_chat_id = 12345
    client.post(f"/tg-chat/{tg_chat_id}")  # регистрируем пользователя
    data = {"url": "https://example.com", "tags": ["news"], "filters": []}
    response = client.post("/links", headers={"tg-chat-id": str(tg_chat_id)}, json=data)
    assert response.status_code == HTTPStatus.OK


def test_add_duplicate_link(client: TestClient) -> None:
    tg_chat_id = 12345
    client.post(f"/tg-chat/{tg_chat_id}")
    data = {"url": "https://example.com", "tags": ["news"], "filters": []}
    client.post("/links", headers={"tg-chat-id": str(tg_chat_id)}, json=data)
    response = client.post("/links", headers={"tg-chat-id": str(tg_chat_id)}, json=data)
    assert response.status_code == HTTPStatus.CONFLICT


def test_delete_link(client: TestClient) -> None:
    tg_chat_id = 12345
    client.post(f"/tg-chat/{tg_chat_id}")
    data = {"url": "https://example.com", "tags": [], "filters": []}
    client.post("/links", headers={"tg-chat-id": str(tg_chat_id)}, json=data)
    response = client.delete(
        "/links", headers={"tg-chat-id": str(tg_chat_id)}, params={"url": "https://example.com"}
    )
    assert response.status_code == HTTPStatus.OK


def test_delete_nonexistent_link(client: TestClient) -> None:
    tg_chat_id = 12345
    client.post(f"/tg-chat/{tg_chat_id}")
    data = {"url": "https://nonexistent.com"}
    response = client.delete("/links", headers={"tg-chat-id": str(tg_chat_id)}, params=data)
    assert response.status_code == HTTPStatus.NOT_FOUND
