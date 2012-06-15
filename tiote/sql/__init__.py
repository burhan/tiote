from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import OperationalError, ProgrammingError, DatabaseError
import datetime

from tiote.utils import fns
import mysql, pgsql


def stored_query(query_type, dialect):
    '''
    Runs queries that are store directly as text and needs no translations. 
    
    It might be removed in the future.
    '''
    if dialect == 'mysql': return mysql.stored_query(query_type)
    elif dialect == 'postgresql': return pgsql.stored_query(query_type)
    
   
def generate_query(query_type, dialect='postgresql', query_data=None):
    '''
    Generates queries of ``query_type`` with the given ``query_data``. Queries here need
    some form(s) of translation.

    Queries common to all dialects are written out here while others are left to their
    own files.
    
    The generated queries are returned as a tuple of strings. 
    '''
    
    # init
    if query_data.has_key('schm'):
        prfx = "{schm}.".format(**query_data) if dialect =='postgresql' else ""
    else: prfx = ""
    #queries
    if query_type == 'get_single_row':
        q0 = "SELECT * FROM {0}{tbl} WHERE {where} LIMIT 1".format(prfx, **query_data)
        return (q0,)

    elif query_type == 'browse_table':
        q0 = "SELECT * FROM {0}{tbl}"
        if query_data.has_key('sort_key') and query_data.has_key('sort_dir'):
            q0 += " ORDER BY {sort_key} {sort_dir}"
        q0 += " LIMIT {limit} OFFSET {offset}"
        return (q0.format(prfx, **query_data),)

    elif query_type == 'count_rows':
        q0 = "SELECT count(*) FROM {0}{tbl}".format(prfx, **query_data)
        return (q0,)

    elif query_type == 'drop_table':
        queries = []
        for where in query_data['conditions']:
            queries.append( "DROP TABLE {0}{table}".format(prfx, **where))
        return tuple(queries)
    
    elif query_type == 'empty_table':
        queries = []
        for where in query_data['conditions']:
            queries.append( "TRUNCATE {0}{table}".format(prfx, **where) )
        return tuple(queries)

    elif query_type == 'delete_row':
        queries = []
        where_stmt = fns.where_frm_conditns( query_data['conditions'] )
        for where_cond in where_stmt:
            q0 = "DELETE FROM {0}{tbl}".format(prfx, **query_data) + " WHERE "+where_cond
            queries.append(q0)
        return tuple(queries)
    
    elif query_type == 'drop_db':
        queries = []
        for where in query_data['conditions']:
            queries.append( "DROP DATABASE {name}".format(**where) )
        return tuple(queries)

    elif query_type == 'drop_column':
        queries = []
        for where in query_data['conditions']:
            sql_stmt = "ALTER TABLE {schm_prefx}{tbl} DROP COLUMN {column}".format(
                schm_prefx=prfx, tbl=query_data['tbl'], **where)
            queries.append(sql_stmt)
        return tuple(queries)
    
    if dialect == 'postgresql':
    	return pgsql.generate_query(query_type, query_data=query_data)
    elif dialect == 'mysql':
    	return mysql.generate_query(query_type, query_data=query_data)


def get_column_sql(dialect, get_data={}, form_data={}):
    queries = []
    i = 0 # this form contains only one BaseColumnForm
    # generation of column creation sequel statements
    first_query = "ALTER TABLE {obj}.{tbl} ADD"
    # dialect dependent
    if dialect == 'postgresql':
        first_query += pgsql.col_defn(form_data, str(i))
    elif dialect == 'mysql':
        first_query += mysql.col_defn(form_data, str(i))
    # default value (common syntax for both dialects)
    default_value = form_data['default_%d' % i]
    if default_value:
        first_query += ' DEFAULT %s' % fns.str_quote(default_value)
    # translate variables
    first_query = first_query.format(
        obj = get_data.get('db') if dialect == 'mysql' else get_data.get('schm'),
        tbl = get_data.get('tbl'),
        **form_data
    )
    # handle column placement in mysql
    if dialect == 'mysql':
        if form_data['insert_position'] == 'at the beginning':
            first_query += ' FIRST'
        elif form_data['insert_position'].count('after '):
            first_query += ' AFTER ' + form_data['insert_position'].split(' ')[1].strip()

    return (first_query, )
