from src.api.schemas.schemas import UpdateInfo


async def make_description(update_info: UpdateInfo) -> str:
    """
    Создать описание обновления
    :param update_info:
    :return:
    """
    date_str = update_info.creation_date
    preview = update_info.preview
    return (
        f"Тема: {update_info.title}\n"
        f"Пользователь: {update_info.user_name}\n"
        f"Дата: {date_str}\n"
        f"Содержание: {preview}"
    )
