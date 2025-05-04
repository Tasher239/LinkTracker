import pytest
from src.api.scrapper_api.utils_scrapper_api import (
    get_stackoverflow_info_api_url,
    github_url_to_api,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url, expected",
    [
        (
            "https://stackoverflow.com/questions/123456",
            "https://api.stackexchange.com/2.3/questions/123456?site=stackoverflow",
        ),
        (
            "https://stackoverflow.com/questions/987654/",
            "https://api.stackexchange.com/2.3/questions/987654?site=stackoverflow",
        ),
        ("https://stackoverflow.com/answer/123456", None),  # Некорректная ссылка
        (
            "https://stackoverflow.com/questions/123456?extra=param",
            "https://api.stackexchange.com/2.3/questions/123456?site=stackoverflow",
        ),
    ],
)
async def test_stackoverflow_url_to_api(url: str, expected: str | None) -> None:
    """Тест: Корректный парсинг ссылок StackOverflow"""
    assert await get_stackoverflow_info_api_url(url) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://github.com/user/repo", "https://api.github.com/repos/user/repo"),
        (
            "https://github.com/user/repo/issues/123",
            "https://api.github.com/repos/user/repo/issues/123",
        ),
        (
            "https://github.com/user/repo/pull/456",
            "https://api.github.com/repos/user/repo/pulls/456",
        ),
        ("https://github.com/user/repo/blob/main/file.py", None),  # Некорректная ссылка
        ("https://github.com/user/repo/", "https://api.github.com/repos/user/repo"),
        (
            "https://github.com/org-name/repo-name",
            "https://api.github.com/repos/org-name/repo-name",
        ),
    ],
)
def test_github_url_to_api(url: str, expected: str | None) -> None:
    """Тест: Корректный парсинг ссылок GitHub"""
    assert github_url_to_api(url) == expected
