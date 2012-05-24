import json

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from urllib import urlencode
from django.utils.datastructures import SortedDict
from tiote import forms
from tiote.views import _abs
from tiote.utils import *


def base_overview(request, **kwargs):
    ''' generates the CompositeTableView for all overview functions '''
    conn_params = fns.get_conn_params(request)

    # generate href with hash ordered as tiote needs
    dest_url = SortedDict(); _d = {'sctn':'db','v':'overview'}
    for k in _d: dest_url[k] = _d[k] # init this way to maintain order
    for k in ('db', 'schm','tbl',): 
        if request.GET.get(k): dest_url[k] = request.GET.get(k)

    c = _abs.CompositeTableView( 
        subnav_list = ('tbl',),
        url_prfx = urlencode(dest_url),
        **kwargs)

    return c.get(request, **kwargs)


def tbl_overview(request):
    '''
    'overview' view of tables. editing, deletion and creation of tables
    '''
    conn_params = fns.get_conn_params(request)
    # table deletion or emptying request catching and handling
    if request.method == 'POST' and request.GET.get('upd8'):
        # format the where_stmt to a mapping of columns to values (a dict)
        l = request.POST.get('where_stmt').strip().split(';')
        conditions = fns.get_conditions(l)
        q = ''
        if request.GET.get('upd8') == 'drop':
            q = 'drop_table'
        elif request.GET.get('upd8') == 'empty':
            q = 'empty_table'
        query_data = {'db':request.GET['db'],'conditions':conditions}
        if request.GET.get('schm'):
            query_data['schm'] = request.GET.get('schm')
        h = qry.rpr_query(conn_params, q , query_data)
        h.set_cookie('TT_UPDATE_SIDEBAR', 'ye') # update sidebar in case there have been a deletion
        return h

    # generate view data
    get_data = fns.qd(request.GET)
    if not get_data.has_key('schm'): get_data['schm'] = 'public'
    tbl_data = qry.rpr_query(conn_params, 'table_rpr', get_data)

    # setup url_prfx with SortedDict to maintain structure
    dest_url = SortedDict(); d = {'sctn':'tbl','v':'browse'}
    for k in d: dest_url[k] = d[k]
    for k in ('db', 'schm',): 
        if request.GET.get(k): dest_url[k] = request.GET.get(k) 
    
    properties = {'keys': (('table', 'key'),), 'go_link': True, 'go_link_type': 'href', 
        'go_link_dest': '#'+urlencode(dest_url)+'&tbl',
        }

    return base_overview(request, tbl_data=tbl_data, tbl_props=properties, show_tbl_optns=True,
        tbl_optn_type='tbl', subv='tbls', empty_err_msg="This database contains no tables")
    

def route(request):
    if request.GET['v'] in ('overview', 'ov'):
        return tbl_overview(request) # default
