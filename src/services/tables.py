from src.configs.config import engine
from functools import lru_cache
from sqlalchemy import Table, MetaData
from sqlalchemy.util import memoized_property

@lru_cache()
class Tables:
    def __init__(self):
        self.metadata = MetaData()
        self.metadata.bind = engine

    @memoized_property
    def users(self):
        return Table("users", self.metadata, autoload_with=engine)

    @memoized_property
    def user_otps(self):
        return Table("user_otps", self.metadata, autoload_with=engine)
    
    @memoized_property
    def user_type(self):
        return Table("user_type", self.metadata, autoload_with=engine)
    
    @memoized_property
    def user_tokens(self):
        return Table("user_tokens", self.metadata, autoload_with=engine)
    
    @memoized_property
    def user_queries(self):
        return Table("user_queries", self.metadata, autoload_with=engine)
    
    @memoized_property
    def chat_history(self):
        return Table("chat_history", self.metadata, autoload_with=engine)
    
    @memoized_property
    def media_uploads(self):
        return Table("media_uploads", self.metadata, autoload_with=engine)
    
    @memoized_property
    def subjects(self):
        return Table("subjects", self.metadata, autoload_with=engine)
    
    @memoized_property
    def conversations(self):
        return Table("conversations", self.metadata, autoload_with=engine)

    
    @memoized_property
    def payments(self):
        return Table("payments", self.metadata, autoload_with=engine)
    
    @memoized_property
    def plans(self):
        return Table("plans", self.metadata, autoload_with=engine)
    
