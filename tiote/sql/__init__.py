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
    
    if dialect == 'postgresql':
    	return pgsql.generate_query(query_type, query_data=query_data)
    elif dialect == 'mysql':
    	return mysql.generate_query(query_type, query_data=query_data)

    	
def full_query(conn_params, query):
    '''
    executes and returns a query result
    '''
    eng = create_engine(get_conn_link(conn_params))
    conn = eng.connect()
    try:
        conn = eng.connect()
        query_result =  conn.execute(text(query))
        d = {}
        l = []
        for row in query_result:
            row = list(row)
            for i in range(len(row)):
                if row[i] == None:
                    row[i] = ""
                elif type( row[i] ) == datetime.datetime:
                    row[i] = row[i].__str__()
            l.append( tuple(row) )
        d =  {'columns': query_result.keys(),'count': query_result.rowcount, 
            'rows': l}
        conn.close()
        return d
    except Exception as e:
        conn.close()
        return str(e)
    
    
def short_query(conn_params, queries):
    """
    executes and returns the success state of the query
    """
    eng = create_engine( get_conn_link(conn_params) )
    conn = ''
    try:
        conn = eng.connect()
        for query in queries:
            query_result = conn.execute(text(query))
        return {'status':'success', 'msg':''}
    except Exception as e:
        conn.close()
        return {'status':'fail', 'msg': str(e) }
    
    
def model_login(conn_params):
    '''
    Utility function which is used to simulate logging a user in.
    
    It checks if the username/password/database combination if given is correct.
    '''
    link = URL(conn_params['database_driver'], username = conn_params['username'],
        password= conn_params['password'], host = conn_params['host'])
    if conn_params['connection_database']:
        link.database = conn_params['connection_database']
    elif not conn_params['connection_database'] and conn_params['database_driver'] == 'postgresql':
        link.database = 'postgres'
    engine = create_engine(link)
    conn = ''
    dict_ret = {}
    try:
        conn = engine.connect()
    except OperationalError as e:
        dict_ret =  {'login': False, 'msg': str(e)}
    else:
        # todo 'msg'
        dict_ret =  {'login': True, 'msg': ''}
        conn.close()
    return dict_ret
 


def get_conn_link(conn_params):
    '''
    SQLAlchemy uses a special syntax for its database descriptors. This utility function
    gets that syntax from the given ``conn_params``
    '''
    return '{dialect}://{username}:{password}@{host}/{db}'.format(**conn_params)

