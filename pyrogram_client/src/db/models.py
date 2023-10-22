import sqlalchemy
from sqlalchemy.orm import DeclarativeBase, declared_attr, relationship, validates
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from settings import settings


class Base(DeclarativeBase):
    id = sqlalchemy.Column(sqlalchemy.BigInteger(), primary_key=True)

    engine = create_async_engine(url=settings.database_url.unicode_string())
    session = async_sessionmaker(bind=engine)

    @declared_attr
    def __tablename__(cls):
        return ''.join([f'_{i.lower()}' if i.isupper() else i for i in cls.__name__]).strip('_')





# class Chat(Base):
#     # is_active = sqlalchemy.Column(sqlalchemy.Boolean(), default=True, nullable=False)
#     # one_time_answer = sqlalchemy.Column(sqlalchemy.Boolean(), default=False, nullable=False)
#
#     def __str__(self):
#         return f'{self.id}'



class Keyword(Base):
    keyword = sqlalchemy.Column(sqlalchemy.String(1056), nullable=False)


    def __str__(self):
        return f'{self.keyword}'

class MinusKeyword(Base):
    minus_keyword = sqlalchemy.Column(sqlalchemy.String(1056), nullable=False)

    def __str__(self):
        return f'{self.minus_keyword}'

class Manager(Base):

    def __str__(self):
        return f'{self.id}'