import json

from django.http import HttpResponse
from django.template import loader, Template
from django.utils.datastructures import SortedDict
from urllib import urlencode
from tiote import forms, sa
from tiote.utils import *
import base


def browse(request):
    conn_params = fns.get_conn_params(request, update_db=True)
    # row(s) deletion request handling
    if request.method == 'POST':
        if request.GET.get('upd8') == 'delete':
            l = request.POST.get('where_stmt').strip().split(';')
            query_data = fns.qd(request.GET)
            query_data['conditions'] = fns.get_conditions(l)
            return qry.rpr_query(conn_params, 'delete_row', query_data)
        else:
            return edit(request)
    
    tbl_data = qry.browse_table(conn_params, request.GET, request.POST)
    # build table
    c = base.TableView(tbl_data=tbl_data,
        tbl_props = {'with_checkboxes': True, 'display_row': True, },
        tbl_store = {'total_count':tbl_data['total_count'], 'pg': tbl_data['pg'],
            'limit': tbl_data['limit'] },
        show_tbl_optns = True,
        tbl_optn_type='data',
        empty_err_msg="This table contains no items",
        # columns_desc=tbl_structure,
        )
    return c.get(request)


def base_struct(request, **kwargs):
    conn_params = fns.get_conn_params(request)
    # get url prefix
    dest_url = SortedDict(); _d = {'sctn':'tbl','v':'struct'}
    for k in _d: dest_url[k] = _d[k] # init this way to maintain order
    for k in ('db', 'schm','tbl',): 
        if request.GET.get(k): dest_url[k] = request.GET.get(k)

    url_prefix = urlencode(dest_url)

    subnav_list = ['cols', 'cons', ] # manually updated as more features are implemented
    if conn_params['dialect'] == 'postgresql': subnav_list.append('deps')

    props = {'props_table': True }
    if kwargs.get('tbl_props'):
        props.update(kwargs.get('tbl_props'))
        kwargs.pop('tbl_props')

    c = base.CompositeTableView(
        url_prfx = url_prefix, 
        subnav_list = subnav_list,
        tbl_props = props,
        **kwargs)

    return c.get(request)


def cols_struct(request):
    # inits and first queries
    conn_params = fns.get_conn_params(request, update_db=True)
    # only needed in the MySQL dialect
    if conn_params['dialect'] == 'mysql':
        charset_list = qry.common_query(conn_params, 'charset_list')['rows']
        supported_engines = qry.common_query(conn_params, 'supported_engines')['rows']
    else:
        supported_engines = None
        charset_list = None
    tbl_names = sa.get_table_names(conn_params, request.GET)
    tbl_cols = qry.rpr_query(conn_params, 'table_structure', fns.qd(request.GET))

    # column editing/deleting
    if request.method == 'POST' and request.GET.get('upd8'):
        # format the where_stmt to a mapping of columns to values (a dict)
        l = request.POST.get('where_stmt').strip().split(';')
        conditions = fns.get_conditions(l)
        # determine query to run
        if request.GET.get('upd8') in ('delete', 'drop',):
            q = 'drop_column'
            query_data = {'conditions': conditions}
            for k in ['db', 'tbl',]: query_data[k] = request.GET.get(k)
            if request.GET.get('schm'):
                query_data['schm'] = request.GET.get('schm')
            
            return qry.rpr_query(conn_params, q, query_data)

    # handle submission of new column form
    elif request.method == 'POST':
        form = forms.ColumnForm(conn_params['dialect'], engines=supported_engines, charsets=charset_list,
            existing_tables=tbl_names, existing_columns=tbl_cols['rows'], label_suffix=':', data=request.POST)
        # handle invalid forms
        if not form.is_valid():
            return fns.response_shortcut(request, template='form_errors',
                extra_vars={'form':form,})
        # prep form fields: add all type_ together
        if conn_params['dialect'] == 'postgresql':
            keys = [key for key in form.cleaned_data.keys() if key.startswith('type_')]
            for key in keys:
                _temp = form.cleaned_data[key].split('|')
                form.cleaned_data[key] = _temp[0] # first index is the base type
                if _temp[-1] != '_default':
                    form.cleaned_data[key] += _temp[1] # the array specifier literal
        # do column creation and return error
        ret = qry.create_column(conn_params, request.GET, form.cleaned_data)
        return HttpResponse(json.dumps(ret))
        
    # table view
    http_resp = base_struct(request, tbl_data=tbl_cols, show_tbl_optns=True,
        tbl_props= {'keys': (('column', 'key'), )}, tbl_optn_type='tbl_like',
        subv='cols', empty_err_msg="Table contains no columns")

    form = forms.ColumnForm(conn_params['dialect'], engines=supported_engines, charsets=charset_list,
        existing_tables=tbl_names, existing_columns=tbl_cols['rows'], label_suffix=':')

    form_html= fns.render_template(request, 'tbl/tt_col.html', context={'form': form, 'edit':False,
        'table_fields': ['name', 'engine', 'charset', 'inherit', 'of_type'],
        'odd_fields': ['type','key','charset', 'not null'],
        'dialect': conn_params['dialect'],
        # 'table_with_columns': table_with_columns,
        }, is_file=True)

    http_resp.content += form_html
    return http_resp


def cons_struct(request):
    conn_params = fns.get_conn_params(request, update_db=True)

    if request.method == "POST" and request.GET.has_key('upd8'):
        # only drop foreign keys is currently supported
        # format the where_stmt to a mapping of keys to values (a dict)
        l = request.POST.get('where_stmt').strip().split(';')
        query_data = {'conditions': fns.get_conditions(l) }
        for k in ['db', 'tbl', 'schm']:
            if request.GET.has_key(k): query_data[k] = request.GET.get(k)
        # decide query to run
        if request.GET.get('upd8') in ('drop', 'delete',): query_type = 'drop_constraint'
        # run and return status of the executed query
        return qry.rpr_query(conn_params, query_type, query_data)

    # view and creation things
    tbl_idxs = qry.rpr_query(conn_params, 'indexes', fns.qd(request.GET))
    return base_struct(request, tbl_data=tbl_idxs, show_tbl_optns=True, subv='cons',
        empty_err_msg="Table contains no constraints",
        tbl_props = {'keys': (('name', 'key'), ('type', 'key'), )},
        tbl_optn_type= 'tbl_like',
        )


def deps_struct(request):
    conn_params = fns.get_conn_params(request, update_db=True)

    # view and deletion things
    tbl_deps = qry.get_dependencies(conn_params, fns.qd(request.GET))
    return base_struct(request, tbl_data=tbl_deps, show_tbl_optns=False,
        subv='deps', empty_err_msg="This table has no dependents")


def insert(request):
    # make queries and inits
    conn_params = fns.get_conn_params(request, update_db=True)
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
    conn_params = fns.get_conn_params(request, update_db=True)
    tbl_struct_data = qry.rpr_query(conn_params, 'raw_table_structure', fns.qd(request.GET))
    # keys = ['column','type','null','default','character_maximum_length','numeric_precision','numeric_scale']
    tbl_indexes_data = qry.rpr_query(conn_params, 'primary_keys', fns.qd(request.GET))

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

        if not f.is_valid():
            # format and return form errors
            ret = {'status': 'fail', 
            'msg': fns.render_template(request,"tt_form_errors.html",
                {'form': f}, is_file=True).replace('\n','')
            }
            return HttpResponse(json.dumps(ret))
        # from here on we are working on a valid form
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


def get_ops_form(conn_params, get_data, data=None):
    context = {}
    if conn_params['dialect'] == 'postgresql':
        # table edit form
        schema_list = qry.common_query(conn_params, 'schema_list', get_data)['rows']
        tblEditForm = forms.get_dialect_form('TableEditForm', conn_params['dialect'])
        context['tbl_edit_form'] = tblEditForm( tbl_name = get_data.get('tbl'),
                tbl_schema = get_data.get('schm'),
                schemas = schema_list,
                data = data
            )
        # table vacuum form
        context['tbl_vacuum_form'] = forms.TableVacuumForm(data=data)

    elif conn_params['dialect'] == 'mysql':
        # table edit form
        charset_list = qry.common_query(conn_params, 'charset_list', get_data)['rows']
        tblEditForm = forms.get_dialect_form('TableEditForm', conn_params['dialect'])
        context['tbl_edit_form'] = tblEditForm(tbl_name= get_data.get('tbl'),
                charsets = charset_list, 
                data = data
            )

    # run validation if data is passed for the forms
    if data is not None:
        for f in context.values(): f.is_valid()
    return context


def ops(request):
    conn_params = fns.get_conn_params(request, update_db=True)
    extra_context = SortedDict({'dialect': conn_params['dialect']})
    if request.method == 'POST':
        form_contxt = get_ops_form(conn_params, request.GET, data=request.POST)
        if request.POST.get('form_type'):
            if request.POST.get('form_type') in ('tbl_vacuum_form', 'tbl_edit_form'):
                form_data = form_contxt[request.POST.get('form_type')].cleaned_data
            else:
                form_data = {} # the other operations don't submit forms
            msg = qry.run_tbl_operations(conn_params, request.POST.get('form_type'), request.GET, form_data)
            return HttpResponse(json.dumps(msg))
        else:
            pass
    else:
        form_contxt = get_ops_form(conn_params, request.GET)

    extra_context.update(form_contxt)

    retrn = fns.render_template(request, 'tbl/tt_ops.html', extra_context, is_file=True )
    return HttpResponse(retrn)

# view router
def route(request):
    if request.GET.get('v') == 'browse':
        if request.GET.get('subv') == 'edit':
            return edit(request)
        return browse(request)

    elif request.GET.get('v') in ('structure', 'struct'):
        if request.GET.get('subv') == 'cons':
            return cons_struct(request)
        elif request.GET.get('subv') == 'deps':
            return deps_struct(request)
        return cols_struct(request) # default

    elif request.GET.get('v') in ('insert', 'ins'):
        return insert(request)
    elif request.GET.get('v') in ('operations', 'ops'):
        return ops(request)
    else:
        return fns.http_500('malformed URL of section "table"')

