import wtforms

from .db.models import Chat, Keyword
from sqladmin import ModelView





class ChatAdmin(ModelView, model=Chat):
    form_include_pk = True
    form_excluded_columns = ['keywords']

class KeywordAdmin(ModelView, model=Keyword):
    column_list = ['keyword', 'chat']
    form_overrides = dict(answer=wtforms.TextAreaField)



def register_view(admin):
    admin.add_view(ChatAdmin)
    admin.add_view(KeywordAdmin)
