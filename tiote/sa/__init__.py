'''
SA = SQLAlchemy
sa induced logic
'''
import datetime
from tiote.utils import *
from sqlalchemy import create_engine, text, sql
from sqlalchemy.engine.url import URL

# engine should be a global thing, should be created once and worked on
_engine = None

def _get_or_set_engine(request):
    global _engine
    conn_params = fns.get_conn_params(request)
    if request.GET.get('db'):
        conn_params['db'] = request.GET.get('db')
    if _engine is None:
        _engine = create_engine(get_conn_link(conn_params), 
                    pool_size=20) # abitrary size: the size was picked up from the SA's docs
    return _engine
# columns things

def full_query(conn_params, query):
    '''
    executes and returns a query result
    '''
    eng = create_engine(get_conn_link(conn_params))
    conn = None
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
    conn = None
    try:
        conn = eng.connect()
        for query in queries:
            query_result = conn.execute(text(query))
    except Exception as e:
        conn.close()
        return {'status':'fail', 'msg': str(e) }
    else:
        return {'status':'success', 'msg':''}
    
    
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

def get_default_schema(request):
    _engine = _get_or_set_engine(request)
    return _engine.dialect._get_default_schema_name(_engine.connect())
