import datetime

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base


def get_table_model(conn_str, table_name):
    engine = sqlalchemy.create_engine(conn_str, convert_unicode=True, echo=False)

    Base = declarative_base(engine)
    Base.metadata.reflect(only=[table_name])
    model = Base.metadata.tables[table_name]
    return model


def statement_to_sql(statement, dialect=None):
    """
    from sqlalchemy.dialects import mysql
    mysql.dialect()
    """
    if dialect is None and statement.bind:
        dialect = statement.bind.dialect
    compiled_sql = str(statement.compile(dialect=dialect, compile_kwargs={"literal_binds": True}))
    return compiled_sql


def fix_mysql_compiler():
    """
    Fix mysql compiler for the DateTime literal value.
    """
    from sqlalchemy.dialects.mysql.base import MySQLCompiler
    from sqlalchemy.sql.sqltypes import DATETIME, DATE, TIME

    def render_datetime(value, type_):
        if isinstance(value, datetime.datetime):
            return repr(value.strftime('%Y-%m-%d %H:%M:%S'))
        elif isinstance(value, datetime.date):
            return repr(value.strftime('%Y-%m-%d'))
        elif isinstance(value, datetime.time):
            return repr(value.strftime('%H:%M:%S'))
        return str(value)

    def my_render_literal_value(self, value, type_):
        if isinstance(type_, (DATETIME, DATE, TIME, sqlalchemy.dialects.mysql.types.DATETIME)):
            value = render_datetime(value, type_)
        elif isinstance(type_, sqlalchemy.dialects.mysql.types.TIMESTAMP):
            value = render_datetime(value, type_)
        else:
            value = super(MySQLCompiler, self).render_literal_value(value, type_)
        if self.dialect._backslash_escapes:
            value = value.replace("\\", "\\\\")
        return value

    MySQLCompiler.render_literal_value = my_render_literal_value
