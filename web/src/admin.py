from typing import Any

from sqlalchemy import delete
from starlette.requests import Request

from .db.models import Keyword, MinusKeyword, Manager, Base
from sqladmin import ModelView as _ModelView

class ModelView(_ModelView):
    async def delete_model(self, request: Request, pk: Any) -> None:
        async with Base.session() as session:
            await session.execute(delete(self.model).filter_by(id=int(pk)))
            await session.commit()





# class ChatAdmin(ModelView, model=Chat):
#     form_include_pk = True
#     form_excluded_columns = ['keywords']



class KeywordAdmin(ModelView, model=Keyword):
    column_list = ['keyword', 'chat']

class MinusKeywordAdmin(ModelView, model=MinusKeyword):
    column_list = ['minus_keyword', 'chat']


class ManagerAdmin(ModelView, model=Manager):
    form_include_pk = True




def register_view(admin):
    # admin.add_view(ChatAdmin)
    admin.add_view(KeywordAdmin)
    admin.add_view(MinusKeywordAdmin)
    admin.add_view(ManagerAdmin)
