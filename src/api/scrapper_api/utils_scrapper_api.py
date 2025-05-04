import http
import httpx
import re
from datetime import datetime, timedelta
from http import HTTPStatus
import pytz
from urllib.parse import urlparse
from typing import Any

from src.api.schemas.schemas import LinkUpdate, UpdateInfo


def github_url_to_api(url: str) -> str | None:
    """
    Преобразует URL GitHub (issue или pull) в соответствующий
    REST-API endpoint или возвращает None, если шаблон не совпал
    :param url:
    :return:
    """
    url = url.rstrip("/")

    pattern = r"https://github\.com/([^/]+)/([^/]+)(?:/(issues|pull)/(\d+))?$"
    match = re.match(pattern, url)

    if match:
        owner, repo, item_type, item_number = match.groups()
        if item_type == "pull":
            item_type = "pulls"
        base_api = f"https://api.github.com/repos/{owner}/{repo}"

        if item_type and item_number:
            return f"{base_api}/{item_type}/{item_number}"

        return base_api

    return None


async def get_stackoverflow_question_id(url: str) -> str | None:
    """
    Извлекает ID вопроса StackOverflow из URL
    или возвращает None, если URL не подходит
    :param url:
    :return:
    """
    pattern = r"https://stackoverflow\.com/questions/(\d+)"
    match = re.match(pattern, url)
    if not match:
        return None
    question_id = match.group(1)
    if match:
        return question_id
    return None


async def get_stackoverflow_info_api_url(url: str) -> str | None:
    """
    Строит API-URL для получения информации о вопросе
    StackOverflow по его ID или возвращает None
    :param url:
    :return:
    """
    question_id = await get_stackoverflow_question_id(url)
    if not question_id:
        return None
    return f"https://api.stackexchange.com/2.3/questions/{question_id}?site=stackoverflow"


async def get_stackoverflow_last_answer_api_url(url: str) -> str | None:
    """
    Строит API-URL для получения списка ответов на вопрос StackOverflow,
    сортированных по времени (последний первым)
    :param url:
    :return:
    """
    question_id = await get_stackoverflow_question_id(url)
    if not question_id:
        return None
    return f"https://api.stackexchange.com/2.3/questions/{question_id}/answers?order=desc&sort=creation&site=stackoverflow&filter=withbody"


async def get_stackoverflow_comments_api_url(url: str) -> str | None:
    """
    Строит API-URL для получения списка комментариев
    к вопросу StackOverflow, сортированных по времени
    :param url:
    :return:
    """
    question_id = await get_stackoverflow_question_id(url)
    if not question_id:
        return None
    return f"https://api.stackexchange.com/2.3/questions/{question_id}/comments?order=desc&sort=creation&site=stackoverflow&filter=withbody"


async def fetch_json_or_none(client: httpx.AsyncClient, url: str | None) -> dict[str, Any] | None:
    """
    Выполняет асинхронный GET-запрос по url и возвращает
    распарсенный JSON или None, если статус ≠ 200.
    :param client:
    :param url:
    :return:
    """
    if not url:
        return None
    resp = await client.get(url)
    if resp.status_code != HTTPStatus.OK:
        return None
    return resp.json()  # type: ignore[no-any-return]


def get_first_item(json_data: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Извлекает первый элемент из поля "items"
    JSON-ответа или возвращает None, если данных нет
    :param json_data:
    :return:
    """
    if not json_data:
        return None
    items = json_data.get("items")
    if not items:
        return None
    return items[0]  # type: ignore[no-any-return]


def pick_latest(
    item_a: dict[str, Any] | None, item_b: dict[str, Any] | None
) -> dict[str, Any] | None:
    """
    Сравнивает creation_date двух объектов и возвращает тот, что свежее
    :param item_a:
    :param item_b:
    :return:
    """
    if not item_a and not item_b:
        return None
    if not item_a:
        return item_b
    if not item_b:
        return item_a

    if item_b.get("creation_date", 0) > item_a.get("creation_date", 0):
        return item_b
    return item_a


async def get_stackoverflow_last_link_upd(url: str) -> UpdateInfo | None:
    """
    Находит самый свежий ответ или комментарий к вопросу StackOverflow,
    проверяет, было ли обновление после нужного времени,
    и возвращает UpdateInfo или None
    :param url:
    :return:
    """
    async with httpx.AsyncClient() as client:
        question_api_url = await get_stackoverflow_info_api_url(url)
        if not question_api_url:
            return None

        info_data = await fetch_json_or_none(client, question_api_url)
        info_item = get_first_item(info_data)
        if not info_item:
            return None

        title = info_item.get("title", "")

        # 2) Самый свежий ответ
        answer_api_url = await get_stackoverflow_last_answer_api_url(url)
        answer_data = await fetch_json_or_none(client, answer_api_url)
        latest_answer = get_first_item(answer_data)

        # 3) Самый свежий комментарий
        comment_api_url = await get_stackoverflow_comments_api_url(url)
        comment_data = await fetch_json_or_none(client, comment_api_url)
        latest_comment = get_first_item(comment_data)

        # 4) Выбираем, что свежее — ответ или комментарий
        latest_item = pick_latest(latest_answer, latest_comment)
        if not latest_item:
            return None

    # 5) Формируем UpdateInfo
    user_name = latest_item.get("owner", {}).get("display_name", "Unknown")
    creation_ts = latest_item.get("creation_date", 0)
    creation_date = datetime.fromtimestamp(creation_ts, pytz.timezone("Europe/Moscow"))
    creation_date_str = creation_date.strftime("%Y-%m-%d %H:%M")

    body = latest_item.get("body", "")
    max_length = 200
    preview = body[:max_length] + "..." if len(body) > max_length else body

    return UpdateInfo(
        title=title,
        user_name=user_name,
        creation_date=creation_date_str,
        preview=preview,
    )


async def get_github_api_url(url: str) -> tuple[str | None, bool]:
    """
    Определяет API URL и возвращает флаг is_direct:
    - True, если ссылка ведёт на конкретный PR или Issue
    - False, если ссылка на репозиторий
    :param url:
    :return:
    """
    pr_issue_pattern = r"https://github\.com/([^/]+)/([^/]+)/(issues|pull)/(\d+)"
    match = re.match(pr_issue_pattern, url)
    if match:
        owner, repo, item_type, number = match.groups()
        if item_type == "issues":
            return f"https://api.github.com/repos/{owner}/{repo}/issues/{number}", True
        elif item_type == "pull":
            return f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}", True
    else:
        owner_repo_pattern = r"https://github\.com/([^/]+)/([^/]+)"
        match = re.match(owner_repo_pattern, url)
        if match:
            owner, repo = match.groups()
            # Запрос списка всех Issue и PR
            return (
                f"https://api.github.com/repos/{owner}/{repo}/issues?state=all&sort=created&direction=desc",
                False,
            )
    return None, False


async def get_github_last_link_update(url: str) -> UpdateInfo | None:
    """
    Получает из GitHub последние данные по issue/PR и
    строит UpdateInfo (заголовок, автор, время, превью).
    :param url:
    :return:
    """
    api_url, is_direct = await get_github_api_url(url)
    if api_url is None:
        return None

    async with httpx.AsyncClient() as client:
        response = await client.get(api_url)
        if response.status_code != http.HTTPStatus.OK:
            return None
        data = response.json()
        if not data:
            return None

        if is_direct:
            # Если ссылка ведёт на конкретный PR или Issue, data — это словарь
            latest_item = data
            # Получаем последний комментарий
            pr_issue_pattern = r"https://github\.com/([^/]+)/([^/]+)/(issues|pull)/(\d+)"
            match = re.match(pr_issue_pattern, url)
            preview = ""
            if match:
                owner, repo, item_type, number = match.groups()
                if item_type == "pull":
                    item_type = "pulls"
                comments_url = f"https://api.github.com/repos/{owner}/{repo}/{item_type}/{number}/comments?sort=created&direction=desc"
                comm_resp = await client.get(comments_url)
                preview = ""
                if comm_resp.status_code == http.HTTPStatus.OK:
                    comments = comm_resp.json()
                    # Если есть комментарии, берем текст последнего (новейшего)
                    if comments:
                        preview = comments[0].get("body")
                    else:
                        preview = ""
        else:
            latest_item = data[0]
            preview = latest_item.get("body") or ""

        title = latest_item.get("title", "")
        username = latest_item.get("user", {}).get("login", "Unknown")

        creation_date = (
            datetime.strptime(latest_item.get("created_at"), "%Y-%m-%dT%H:%M:%SZ")
            .replace(tzinfo=pytz.utc)
            .astimezone(pytz.timezone("Europe/Moscow"))
        )
        creation_date_str = creation_date.strftime("%Y-%m-%d %H:%M")

        max_length = 200
        preview = preview[:max_length] + "..." if len(preview) > max_length else preview

    return UpdateInfo(
        title=title,
        user_name=username,
        creation_date=creation_date_str,
        preview=preview,
    )


async def check_last_update(url: str) -> UpdateInfo | None:
    """
    В зависимости от домена (github.com или stackoverflow.com)
    вызывает соответствующую функцию, проверяет, было ли обновление
    «в нужное окно» (между 10:00 и 22:00 МСК) и возвращает UpdateInfo или None
    :param url:
    :return:
    """
    domain = urlparse(url).netloc
    if "github.com" in domain:
        last_link_update = await get_github_last_link_update(url)
    elif "stackoverflow.com" in domain:
        last_link_update = await get_stackoverflow_last_link_upd(url)
    else:
        return None

    if last_link_update is None:
        return None

    """
    для тестирования
    tmp = now_time.replace(hour=17, minute=0, second=0, microsecond=0) - timedelta(days=10)
    return last_updated_time > tmp
    """

    have_new_message = False
    last_link_update_time = pytz.timezone("Europe/Moscow").localize(
        datetime.strptime(last_link_update.creation_date, "%Y-%m-%d %H:%M")
    )

    now_time = datetime.now(pytz.timezone("Europe/Moscow")).replace(
        year=2020, hour=10, minute=0, second=0, microsecond=0
    )
    match now_time.hour:
        case 10:
            have_new_message = last_link_update_time > now_time.replace(
                hour=22, minute=0, second=0, microsecond=0
            ) - timedelta(days=1)
        case 22:
            have_new_message = last_link_update_time > now_time.replace(
                hour=10, minute=0, second=0, microsecond=0
            )

    if have_new_message:
        return last_link_update
    return None
