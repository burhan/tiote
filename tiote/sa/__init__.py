'''
SA = SQLAlchemy
sa induced logic
'''
import datetime
from tiote.utils import *
from sqlalchemy import create_engine, text, sql, MetaData
from sqlalchemy.engine.url import URL


def _get_engine(conn_params,):
    return create_engine(get_conn_link(conn_params),
            pool_size=20) # abitrary size: the size was picked up from the SA's docs

# columns things

def full_query(conn_params, query):
    '''
    executes and returns a query result
    '''
    eng = create_engine(get_conn_link(conn_params))
    try:
        conn = eng.connect()
        if type(query) in (str, unicode):
            query_result =  conn.execute(text(query))
        else: query_result = conn.execute(query)
    except Exception as e:
        conn.close()
        return str(e)
    else:
        d = {}; l = []
        for row in query_result:
            row = list(row)
            for i in range(len(row)):
                if row[i] == None: row[i] = u""
                elif type( row[i] ) == datetime.datetime:
                    row[i] = unicode(row[i])
            l.append( tuple(row) )
        d =  {u'columns': query_result.keys(),u'count': query_result.rowcount, 
            u'rows': l}
        conn.close()
        return d
    
def short_query(conn_params, queries):
    """
    executes and returns the success state of the query
    """
    eng = create_engine( get_conn_link(conn_params) )
    try:
        conn = eng.connect()
        for query in queries:
            query_result = conn.execute(text(query))
    except Exception as e:
        conn.close()
        return {'status':'fail', 'msg': str(e) }
    else:
        conn.close()
        return {'status':'success', 'msg':''}
    
    
def model_login(login_params):
    '''
    Utility function which is used to simulate logging a user in.
    
    It checks if the username/password/database combination if given is correct.
    '''
    login_params['db'] = login_params.pop('connection_database')
    login_params['dialect'] = login_params.pop('database_driver')
    if not login_params['db'] and login_params['dialect'] == 'postgresql':
        login_params['db'] = 'postgres'
    engine = _get_engine(login_params)
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

        
def parse_sa_result(ds, order = None):
    '''
    parses a list of dictionary as returned by some SA modules
    returns a dict of keys, columns, count
    '''
    # generate columns
    # use the first key as a template for the order if the order is not explicity given
    if order: _order = order
    else: _order = l[0].keys()

    # get rows
    rows = []
    for sing_desc in ds:
        row = [sing_desc[k] for k in _order]
        rows.append(row)
    return {'columns':_order, 'rows': rows, 'count': len(ds)}


def transform_args_to_bindparams(argmap):
    '''argmap is a dict '''
    _l = []
    for key, value in argmap.iteritems():
        _l.append(sql.bindparam(key, value))
    return _l

def get_default_schema(conn_params):
    _engine = _get_engine(conn_params)
    return _engine.dialect._get_default_schema_name(_engine.connect())


def get_table_names(conn_params, get_data={}):
    ''' return the existing tables in a db connection '''
    if not get_data.has_key('tbl'):
        raise KeyError('tbl')

    _engine = _get_engine(conn_params)
    return _engine.dialect.get_table_names(_engine.connect(),
        schema=get_data.get('schm', None) )

def execute_outside_transaction(conn_params, stmts):
    '''
    runs short queries without transactions. SA includes transactions by default for all its
    execution. This causes issues with some particular queries such as dropping databases.
    This queries then make use of psycopg2 directly instead of SA's abstractions.
    '''
    import psycopg2
    conn = psycopg2.connect("dbname=%s user=%s password=%s" % 
        (conn_params['db'], conn_params['username'], conn_params['password'])
        )
    conn.autocommit = True # disable transactions
    # conn.set_isolation
    cur = conn.cursor()
    try:
        for stmt in stmts:
            cur.execute(stmt)
    except Exception as e:
        cur.close()
        conn.close()
        return {'status':'fail', 'msg': str(e) }
    else:
        cur.close()
        conn.close()
        return {'status':'success', 'msg':''}


# implementation incomplete
def insert(conn_params, get_data={}, post_data={}):
    # get_data must have key 'tbl'
    if not get_data.get('tbl'):
        raise KeyError('tbl ')

    engine = _get_engine(conn_params, get_data)
    meta = MetaData()
    meta.bind = engine

    tbl = Table(get_data.get('tbl'), meta, autoload=True,
        schema_name = get_data.get('schm'))


def get_fkeys_definitn(conn_params, get_data={}, ):
    if not get_data.has_key('tbl'):
        raise KeyError('tbl')

    _engine = _get_engine(conn_params)
    fkeys_definitns = _engine.dialect.get_foreign_keys(_engine.connect(), get_data.get('tbl'), 
        schema = get_data.get('schm') if get_data.has_key('schm') else None
        )
    # when there are not foreign keys for this table
    if len(fkeys_definitns) == 0:
        return {'count': len(fkeys_definitns)}
    # make the structure fkeys_definitns be compatible with that used in BareTableView    
    columns = fkeys_definitns[0].keys() # use the first definition to get the column names
    rows = []
    for definitn in fkeys_definitns: # definitn is a dict object
        _temp = definitn.values()
        # the second and last items is a list of columns
        # transform it to a comma seperated list of each of the columns
        for _index in [1, -1]:
            _temp[_index] = ", ".join( _temp[_index] )
        rows.append(_temp)
    tbl_data = {'rows': rows, 'columns': columns, 'count': len(fkeys_definitns)}
    # we're done
    return tbl_data

