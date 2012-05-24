import json

from django.http import HttpResponse
from django.template import loader, Template
from django.utils.datastructures import SortedDict
from urllib import urlencode
from tiote import forms, sa
from tiote.utils import *
from tiote.views import base


def browse(request):
    conn_params = fns.get_conn_params(request)
    # row(s) deletion request handling
    if request.method == 'POST' and request.GET.get('upd8') == 'delete':
        return qry.rpr_query(conn_params, 'delete_row', 
            fns.qd(request.GET), fns.qd(request.POST))
    
    tbl_data = qry.rpr_query(conn_params, 'browse_table',
        fns.qd(request.GET), fns.qd(request.POST))
    
    c = base.TableView(tbl_data=tbl_data,
        tbl_props = {'with_checkboxes': True, 'display_row': True,},
        tbl_store = {'total_count':tbl_data['total_count'], 'offset': tbl_data['offset'],
            'limit': tbl_data['limit'] },
        show_tbl_optns = True,
        tbl_optn_type='data',
        empty_err_msg="This table contains no items"
        )
    return c.get(request)


def base_struct(request, **kwargs):
    # get url prefix
    dest_url = SortedDict(); _d = {'sctn':'tbl','v':'struct'}
    for k in _d: dest_url[k] = _d[k] # init this way to maintain order
    for k in ('db', 'schm','tbl',): 
        if request.GET.get(k): dest_url[k] = request.GET.get(k)

    url_prefix = urlencode(dest_url)

    c = base.CompositeTableView(
        url_prfx = url_prefix, 
        subnav_list = ('cols', 'idxs',),
        **kwargs)

    return c.get(request)


def cols_struct(request):
    conn_params = fns.get_conn_params(request)

    # column editing/deleting
    if request.method == 'POST' and request.GET.get('upd8'):
        l = request.POST.get('whereToEdit').strip().split(';')
        conditions = fns.get_conditions(l)
        
        if request.GET.get('upd8') == 'delete':
            q = 'delete_column'
            query_data = {'db': request.GET.get('db'), 'table': request.GET.get('table'),
                'conditions': conditions}
            
            return qry.rpr_query(conn_params, q, query_data)

    # table view
    tbl_cols = qry.rpr_query(conn_params, 'table_structure', fns.qd(request.GET))
    return base_struct(request, tbl_data=tbl_cols, show_tbl_optns=False, 
        subv='cols', empty_err_msg="Table contains no indexes")


def idxs_struct(request):
    conn_params = fns.get_conn_params(request)

    if request.method == 'POST':
        pass

    # view and creation things
    tbl_idxs = qry.rpr_query(conn_params, 'indexes', fns.qd(request.GET))
    return base_struct(request, tbl_data=tbl_idxs, show_tbl_optns=False, 
        subv='idxs', empty_err_msg="Table contains no columns")


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
        if request.GET.get('subv') == 'idxs':
            return idxs_struct(request)
        return cols_struct(request) # default
    elif request.GET.get('v') in ('insert', 'ins'):
        return insert(request)
    else:
        return fns.http_500('malformed URL of section "table"')
