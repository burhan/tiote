from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import OperationalError, ProgrammingError, DatabaseError
import datetime

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
    prfx = "{schm}.".format(**query_data) if dialect =='postgresql' else ""

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
            where['table'] = where['table'].replace("'", "")
            queries.append( "DROP TABLE {0}{table}".format(prfx, **where))
        return tuple(queries)
    
    elif query_type == 'empty_table':
        queries = []
        for where in query_data['conditions']:
            where['table'] = where['table'].replace("'", "")
            queries.append( "TRUNCATE {0}{table}".format(prfx, **where) )
        return tuple(queries)

    elif query_type == 'delete_row':
        queries = []
        for whereCond in query_data['where_stmt'].split(';'):
            q0 = "DELETE FROM {0}{tbl}".format(prfx, **query_data) + " WHERE "+whereCond
            queries.append(q0)
        return tuple(queries)
    
    elif query_type == 'drop_db':
        queries = []
        for where in query_data['conditions']:
            where['name'] = where['name'].replace("'", "")
            queries.append( "DROP DATABASE {name}".format(**where) )
        return tuple(queries)
    
    
    if dialect == 'postgresql':
    	return pgsql.generate_query(query_type, query_data=query_data)
    elif dialect == 'mysql':
    	return mysql.generate_query(query_type, query_data=query_data)

    	