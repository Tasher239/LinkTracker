import pytest
from src.api.schemas.schemas import AddLinkRequest
from src.database.orm_database import OrmDbProcessor


@pytest.mark.asyncio
async def test_add_and_get_user(orm_db_processor: OrmDbProcessor):
    tg_chat_id = 12345
    await orm_db_processor.add_user(tg_chat_id)
    links = await orm_db_processor.get_user_links(tg_chat_id)
    assert isinstance(links, list)
    assert len(links) == 0


@pytest.mark.asyncio
async def test_add_link_for_user_and_get_links(orm_db_processor: OrmDbProcessor):
    tg_chat_id = 54321
    await orm_db_processor.add_user(tg_chat_id)
    add_link_req = AddLinkRequest(url="http://example.com", tags=["news"], filters=["filter1"])
    link_id = await orm_db_processor.add_link_for_user(tg_chat_id, add_link_req)
    assert isinstance(link_id, int)
    links = await orm_db_processor.get_user_links(tg_chat_id)
    assert len(links) == 1
    link = links[0]
    assert link.id == link_id
    assert link.url == "http://example.com"
    assert link.tags == ["news"]
    assert link.filters == ["filter1"]


@pytest.mark.asyncio
async def test_delete_chat(orm_db_processor: OrmDbProcessor):
    tg_chat_id = 11111
    await orm_db_processor.add_user(tg_chat_id)
    deleted = await orm_db_processor.delete_chat(tg_chat_id)
    assert deleted is True
    deleted_again = await orm_db_processor.delete_chat(tg_chat_id)
    assert deleted_again is False


@pytest.mark.asyncio
async def test_remove_user_link(orm_db_processor: OrmDbProcessor):
    tg_chat_id = 22222
    await orm_db_processor.add_user(tg_chat_id)
    add_link_req = AddLinkRequest(url="http://remove-link.com", tags=["tag1"], filters=["filter1"])
    link_id = await orm_db_processor.add_link_for_user(tg_chat_id, add_link_req)
    result = await orm_db_processor.remove_user_link(tg_chat_id, "http://remove-link.com")
    assert result is not None
    removed_link_id, tags, filters = result
    assert removed_link_id == link_id
    assert tags == ["tag1"]
    assert filters == ["filter1"]
    links = await orm_db_processor.get_user_links(tg_chat_id)
    assert len(links) == 0
