from pydantic import BaseModel, HttpUrl, validator


class ApiErrorResponse(BaseModel):
    description: str
    code: str
    exception_name: str
    exception_message: str
    stacktrace: list[str]


class LinkUpdate(BaseModel):
    id: int
    url: str
    description: str
    tg_chat_id: int


class ListLinksUpdate(BaseModel):
    links: list[LinkUpdate]


class LinkResponse(BaseModel):
    id: int
    url: str
    tags: list[str]
    filters: list[str]


class AddLinkRequest(BaseModel):
    url: str
    tags: list[str]
    filters: list[str]


class ListLinksResponse(BaseModel):
    links: list[LinkResponse]
    size: int


class RemoveLinkRequest(BaseModel):
    url: str


class UpdateInfo(BaseModel):
    title: str
    user_name: str
    creation_date: str
    preview: str
