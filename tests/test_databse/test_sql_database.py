import pytest
from src.database.sql_database import SqlDbProcessor
from src.api.schemas.schemas import AddLinkRequest


@pytest.mark.asyncio
async def test_add_and_get_user(sql_db_processor: SqlDbProcessor):
    tg_chat_id = 12345
    await sql_db_processor.add_user(tg_chat_id)
    links = await sql_db_processor.get_user_links(tg_chat_id)
    assert isinstance(links, list)
    assert len(links) == 0


@pytest.mark.asyncio
async def test_delete_chat(sql_db_processor: SqlDbProcessor):
    tg_chat_id = 11111
    await sql_db_processor.add_user(tg_chat_id)
    deleted = await sql_db_processor.delete_chat(tg_chat_id)
    assert deleted is True
    deleted_again = await sql_db_processor.delete_chat(tg_chat_id)
    assert deleted_again is False


@pytest.mark.asyncio
async def test_remove_user_link(sql_db_processor: SqlDbProcessor):
    tg_chat_id = 22222
    await sql_db_processor.add_user(tg_chat_id)
    add_link_req = AddLinkRequest(url="http://remove-link.com", tags=["tag1"], filters=["filter1"])
    link_id = await sql_db_processor.add_link_for_user(tg_chat_id, add_link_req)
    result = await sql_db_processor.remove_user_link(tg_chat_id, "http://remove-link.com")
    assert result is not None
    removed_link_id, tags, filters = result
    assert removed_link_id == link_id
    assert tags == ["tag1"]
    assert filters == ["filter1"]
    links = await sql_db_processor.get_user_links(tg_chat_id)
    assert len(links) == 0
