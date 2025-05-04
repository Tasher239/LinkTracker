from sqlalchemy import BigInteger, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):  # type: ignore[misc]
    pass


class User(Base):  # type: ignore[misc]
    __tablename__ = "users"

    tg_chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_links: Mapped[list["UserLink"]] = relationship(
        "UserLink",
        back_populates="user",
        lazy="joined",
        cascade="all, delete-orphan",
    )


class Link(Base):  # type: ignore[misc]
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    link_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    user_links: Mapped[list["UserLink"]] = relationship(
        "UserLink",
        back_populates="link",
        lazy="joined",
        cascade="all, delete-orphan",
    )


class UserLink(Base):  # type: ignore[misc]
    __tablename__ = "user_links"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.tg_chat_id", ondelete="CASCADE"), primary_key=True
    )
    link_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("links.id", ondelete="CASCADE"), primary_key=True
    )
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    filters: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    user: Mapped["User"] = relationship("User", back_populates="user_links", lazy="joined")
    link: Mapped["Link"] = relationship("Link", back_populates="user_links", lazy="joined")
