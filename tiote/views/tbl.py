import json

from django.http import HttpResponse
from django.template import loader, Template
from django.utils.datastructures import SortedDict
from urllib import urlencode
from tiote import forms, sa
from tiote.utils import *
from tiote.views import _abs


def browse(request):
    conn_params = fns.get_conn_params(request)
    # row(s) deletion request handling
    if request.method == 'POST' and request.GET.get('upd8') == 'delete':
        return qry.rpr_query(conn_params, 'delete_row', 
            fns.qd(request.GET), fns.qd(request.POST))
    
    tbl_data = qry.rpr_query(conn_params, 'browse_table',
        fns.qd(request.GET), fns.qd(request.POST))
    
    c = _abs.TableView(tbl_data=tbl_data,
        tbl_props = {'with_checkboxes': True, 'display_row': True,},
        tbl_store = {'total_count':tbl_data['total_count'], 'offset': tbl_data['offset'],
            'limit': tbl_data['limit'] },
        show_tbl_optns = True,
        tbl_optn_type='data',
        )
    return c.get(request)


def structure(request):
    conn_params = fns.get_conn_params(request)
    # column deletion
    if request.method == 'POST' and request.GET.get('upd8'):
        l = request.POST.get('whereToEdit').strip().split(';');
        conditions = fns.get_conditions(l)
        q = ''
        if request.GET.get('upd8') == 'edit':
            q = 'drop_table'
            return HttpResponse('update not yet implemented!')
        elif request.GET.get('upd8') == 'delete':
            q = 'delete_column'
            query_data = {'db': request.GET.get('db'), 'table': request.GET.get('table'),
                          'conditions': conditions}
            
            return qry.rpr_query(conn_params, q, query_data)
        
    # view data
    static_addr = fns.render_template(request, '{{STATIC_URL}}')
    subv = request.GET.get('subv', 'cols')
    d = {}
    _subnav = {'cols': fns.ABBREVS['cols'], 'idxs':fns.ABBREVS['idxs']}
    if subv == 'cols':
        d['title'] = _subnav[subv]
#        tbl_struct_data = qry.rpr_query(conn_params, 'table_structure', fns.qd(request.GET))
#        columns_table = htm.HtmlTable(attribs = {'id': 'tbl_columns'},
#            props = {'count': tbl_struct_data['count'], 'with_checkboxes': True,},
#            static_addr = static_addr, **tbl_struct_data
#        )
        eng = sa._get_or_set_engine(request)
        ds = sa.tbl_cols_desc(eng, request.GET.get('tbl'), request.GET.get('schm'))
        order = ['name', 'type', 'nullable', 'default']
        columns_table = htm.SAHtmlTable(ds, order=order, 
            props = {'count': len(ds), 'with_checkboxes': True, 'keys': (('name', 'key'), )},
            static_addr = static_addr)
        
        d['table'] = columns_table.to_element() if columns_table.has_body() \
            else '<div class="undefined">[Table contains no columns]</div>'
    elif subv == 'idxs':
        d['title'] = _subnav[subv]
        indexes_data = qry.rpr_query(conn_params, 'indexes', fns.qd(request.GET))
        indexes_table = htm.HtmlTable(static_addr = static_addr,
            props = {'count': indexes_data['count'], 'with_checkboxes': True},
            **indexes_data
        )
        d['table'] = indexes_table.to_element() if indexes_table.has_body() \
            else '<div class="undefined">[Table contains no indexes]</div>'
    # generate arranged href
    dest_url = SortedDict(); _d = {'sctn':'tbl','v':'struct'}
    for k in _d: dest_url[k] = _d[k] # init this way to maintain order
    for k in ('db', 'schm','tbl',): 
        if request.GET.get(k): dest_url[k] = request.GET.get(k)
    _l = []
    # generate navigation ul
    for k in ('cols', 'idxs',):
        _l.append('<li{0}><a href="{1}{2}">{3}<span>|</span></a></li>'.format(
            ' class="active"' if _subnav[k].lower() == d['title'].lower() else '',
            '#'+urlencode(dest_url)+'&subv=', k, _subnav[k])
        )
    ret_str = '<div style="margin-bottom:-5px;"><ul class="subnav">{0}</ul></div>{table}'.format(
         "".join(_l),**d)
    return HttpResponse(ret_str)


def insert(request):
    # make queries and inits
    conn_params = fns.get_conn_params(request)
    tbl_struct_data = qry.rpr_query(conn_params, 'raw_table_structure', fns.qd(request.GET))
    # keys = ['column','type','null','default','character_maximum_length','numeric_precision','numeric_scale']
    tbl_indexes_data = qry.rpr_query(conn_params, 'indexes', fns.qd(request.GET))

    if request.method == 'POST':
        # the form is a submission so it doesn't require initialization from a database request
        # every needed field would already be in the form (applies to forms for 'edit' view)
        form = forms.InsertForm(tbl_struct=tbl_struct_data, dialect=conn_params['dialect'],
            tbl_indexes=tbl_indexes_data['rows'], data=request.POST)
        # validate form
        if form.is_valid():
            ret = qry.insert_row(conn_params, fns.qd(request.GET), 
                fns.qd(request.POST))

            return HttpResponse(json.dumps(ret))
        else: # form contains error
            ret = {'status': 'fail', 
            'msg': fns.render_template(request,"tt_form_errors.html",
                {'form': form}, is_file=True).replace('\n','')
            }
            return HttpResponse(json.dumps(ret))

    form = forms.InsertForm(tbl_struct=tbl_struct_data, dialect=conn_params['dialect'],
        tbl_indexes=tbl_indexes_data['rows'])

    return fns.response_shortcut(request, extra_vars={'form':form,}, template='form')


def edit(request):
    # get METHOD is not allowed. the POST fields which was used to intialized the form
    # - would not be availble. Redirect the page to the mother page ('v' of request.GET )
    if request.method == 'GET':
        h = HttpResponse(''); d = SortedDict()
        for key in ('sctn', 'v', 'db', 'schm', 'tbl'):
            if request.GET.get(key): d[key] = request.GET.get(key)
        h.set_cookie('TT_NEXT', str( urlencode(d) )  )
        return h
    # inits and queries
    conn_params = fns.get_conn_params(request)
    tbl_struct_data = qry.rpr_query(conn_params, 'raw_table_structure', fns.qd(request.GET))
    # keys = ['column','type','null','default','character_maximum_length','numeric_precision','numeric_scale']
    tbl_indexes_data = qry.rpr_query(conn_params, 'indexes', fns.qd(request.GET))

    # generate the form(s)
    if request.method == 'POST' and request.POST.get('where_stmt'):
        # parse the POST structure and generate a list of dict.
        l = request.POST.get('where_stmt').strip().split(';')
        conditions = fns.get_conditions(l)
        # loop through the dict, request for the row which have _dict as its where clause
        # - and used that information to bind the EditForm
        _l_forms = []
        for _dict in conditions:
            single_row_data = qry.rpr_query(conn_params, 'get_single_row',
                fns.qd(request.GET), _dict
            )
            # make single row data a dict mapping of columns to rows
            init_data = dict(  zip( single_row_data['columns'], single_row_data['rows'][0] )  )
            # create form and store in a the forms list
            f = forms.EditForm(tbl_struct=tbl_struct_data, dialect=conn_params['dialect'],
                tbl_indexes=tbl_indexes_data['rows'], initial=init_data)
            _l_forms.append(f)

        return fns.response_shortcut(request, extra_vars={'forms':_l_forms,}, template='multi_form')
    # submissions of a form
    else:
        f = forms.EditForm(tbl_struct=tbl_struct_data, dialect=conn_params['dialect'],
            tbl_indexes=tbl_indexes_data['rows'], data = request.POST)
        if f.is_valid():
            # two options during submission: update_row or insert_row
            if f.cleaned_data['save_changes_to'] == 'insert_row':
                # pretty straight forward (lifted from insert view above)
                ret = qry.insert_row(conn_params, fns.qd(request.GET), 
                    f.cleaned_data)

                return HttpResponse(json.dumps(ret))
            else:
                indexed_cols = fns.parse_indexes_query(tbl_indexes_data['rows'])
                ret = qry.update_row(conn_params, indexed_cols, 
                    fns.qd(request.GET), f.cleaned_data)

                return HttpResponse(json.dumps(ret))

        else:
            # format and return form errors
            ret = {'status': 'fail', 
            'msg': fns.render_template(request,"tt_form_errors.html",
                {'form': f}, is_file=True).replace('\n','')
            }
            return HttpResponse(json.dumps(ret))



# view router
def route(request):
    if request.GET.get('subv') == 'edit':
        return edit(request)
    elif request.GET.get('v') == 'browse':
        return browse(request)
    elif request.GET.get('v') in ('structure', 'struct'):
        return structure(request)
    elif request.GET.get('v') in ('insert', 'ins'):
        return insert(request)
    else:
        return fns.http_500('malformed URL of section "table"')
