'''
SA = SQLAlchemy
sa induced logic
'''
from tiote.utils import *
from tiote.sql import get_conn_link
from sqlalchemy import create_engine, text, sql

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

def tbl_cols_desc(engine, table_name, schema_name=None, ):
    '''
    '''
    try: conn = engine.connect()
    except Exception, e: raise e # for now
    else:
        cols_desc = engine.dialect.get_columns(conn, table_name, schema=schema_name)
        
        return cols_desc
        
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
