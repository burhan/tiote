import json
from django.http import HttpResponse
from django.conf import settings

from tiote import sql, sa
import fns


def rpr_query(conn_params, query_type, get_data={}, post_data={}):
    '''
    Run queries that have to be generated on the fly. Most queries depends on get_data, 
    while some few depends on post_data

    get_data and post_data are gotten from request.GET and request.POST or form.cleaned_data

    some functions in this file should have been (and previously have been) in this function. but 
    the contents of a function are not indexed by IDEs and that makes debugging difficult
    '''
    # common queries that returns success state as a dict only
    no_return_queries = ('create_user', 'drop_user', 'create_db','create_table',
        'drop_table', 'empty_table', 'delete_row', 'create_column', 'drop_column',
        'drop_db', 'drop_sequence', 'reset_sequence', 'drop_constraint', )
    
    psycopg2_queries = ('drop_db', )

    if query_type in no_return_queries:
        conn_params['db'] = get_data['db'] if get_data.has_key('db') else conn_params['db']
        query_data = {}
        query_data.update(get_data, **post_data)
        queries = sql.generate_query( query_type, conn_params['dialect'],query_data)

        if conn_params['dialect'] == 'postgresql' and query_type in psycopg2_queries:
            # this queries needs to be run outside a transaction block
            # SA execute functions runs all its queries inside a transaction block
            result = sa.execute_outside_transaction(conn_params, queries)
        else: result = sa.short_query(conn_params, queries)
        return HttpResponse( json.dumps(result) )
    
    # specific queries with implementations similar to both dialects
        
    elif query_type in ('indexes', 'primary_keys', 'foreign_key_relation'):
        if conn_params['dialect'] == 'postgresql' and query_type == 'indexes':
            return get_constraints(conn_params, query_type, get_data)

        r = sa.full_query(conn_params,
            sql.generate_query(query_type, conn_params['dialect'], get_data)[0])
        return r

    elif query_type in ('get_single_row',):
        sub_q_data = {'tbl': get_data['tbl'],'db':get_data['db']}
        if get_data.has_key('schm'):
            sub_q_data['schm'] = get_data['schm']
        # generate where statement
        sub_q_data['where'] = ""
        for ind in range(len(post_data)):
            sub_q_data['where'] += post_data.keys()[ind].strip() + "=" 
            val = post_data.values()[ind].strip()
            sub_q_data['where'] += fns.quote(val)
            if ind != len(post_data) - 1: sub_q_data['where'] += ' AND '
        # retrieve and run queries
        conn_params['db'] = get_data['db']
        # assert False
        q = sql.generate_query(query_type, conn_params['dialect'], sub_q_data)
        r =  sa.full_query(conn_params, q[0])
        return r
        

    elif query_type in ('table_rpr', 'table_structure', 'raw_table_structure', 'seqs_rpr'):
        sub_q_data = {'db': get_data['db'],}
        if get_data.has_key('tbl'):
            sub_q_data['tbl'] = get_data['tbl']
        if get_data.has_key('schm'):
            sub_q_data['schm'] = get_data['schm']
        # make query
        if conn_params['dialect'] == 'postgresql' and query_type == 'raw_table_structure':
            q = 'table_structure'
        else: q = query_type

        r = sa.full_query(conn_params,
            sql.generate_query(q, conn_params['dialect'], sub_q_data)[0] )
        # further needed processing
        if conn_params['dialect'] == 'postgresql' and query_type.count('table_structure'):
            rwz = []
            for tuple_row in r['rows']:
                row = list(tuple_row)
                data_type_str = row[1]
                _l = [ data_type_str ]
                datetime_precision = row[7]
                if data_type_str in ('bit', 'bit varying', 'character varying', 'character') and type(row[4]) is int:
                    _l.append( '({0})'.format(row[4]) )
                # elif data_type_str in ('numeric', 'decimal') and type(row[5]) is int or type(row[6]) is int:
                elif data_type_str in ('numeric', 'decimal'):
                    numeric_precision, numeric_scale = row[5], row[6]
                    _l.append( '(%d,%d)' % (numeric_precision, numeric_scale) )
                # interval types should need some revising
                elif data_type_str in ('interval', ):
                    _l.append( '(%d)' % datetime_precision )
                # time and timestamps have a somewhat different declarative syntax
                elif datetime_precision is int and (data_type_str.startswith('time') or data_type_str.startswith('timestamp')):
                    _in = 9 if data_type_str.startswith('timestamp') else 4 # the length of time and timestamp respectively
                    _l = [ data_type_str[:_in], '(%d)' % datetime_precision , data_type_str[_in:]]
                # append the current row to rwz
                if query_type == 'table_structure': rwz.append([row[0], "".join(_l), row[2], row[3] ])
                elif query_type == 'raw_table_structure': 
                    row.append("".join(_l))
                    rwz.append(row)
            # change r['rows']
            r['rows'] = rwz
            # change r['columns']
            if query_type == 'table_structure':
                r['columns'] = [ r['columns'][0], r['columns'][1], r['columns'][2], r['columns'][3] ]
            elif query_type == 'raw_table_structure': r['columns'].append('column_type')

        return r
        
    # queries with dissimilar implementations 
    elif conn_params['dialect'] == 'mysql':
        
        if query_type == 'describe_databases':
            conn_params['db'] = 'INFORMATION_SCHEMA';
            query = sql.stored_query(query_type, conn_params['dialect'])
            return sa.full_query(conn_params, query)
        
        else:
            return fns.http_500('query not yet implemented!')
    else:
        return fns.http_500('dialect not supported!')


def browse_table(conn_params, get_data={}, post_data={}):
    # initializations
    sub_q_data = {'tbl': get_data.get('tbl'),'db':get_data.get('db')}
    pg_index = get_data.get('pg', 1) # page 1 is the starting point
    sub_q_data['limit'] = getattr(settings, 'TT_MAX_ROW_COUNT', 30) # 30 is the default row limit
    # page 1 starts with offset 0 and so on
    sub_q_data['offset'] = int(sub_q_data['limit']) * ( int(pg_index) - 1)
    for item in ('schm', 'sort_key', 'sort_dir',):
        if get_data.has_key(item): sub_q_data[item] = get_data.get(item)
    # retrieve and run queries
    keys = rpr_query(conn_params, 'primary_keys', sub_q_data)
    count = sa.full_query(conn_params, 
        sql.generate_query('count_rows', conn_params['dialect'], sub_q_data)[0],
        )['rows']
    # get the table's row listing
    r = sa.full_query(conn_params,
        sql.generate_query('browse_table', conn_params['dialect'], sub_q_data)[0]
        )
    # format and return data
    if type(r) == dict:
        r.update({
            'total_count': count[0][0],
            'pg': pg_index,
            'limit':sub_q_data['limit'],
            'keys': keys
        })
        return r
    else:
        return fns.http_500(r)


def fn_query(conn_params, query_name, get_data={}, post_data={}):
    '''
    reduces the growth rate of the rpr_query function above
    
    it uses a mapping to know which function to call
    
    all its queries are functions to be called not sections of stored logic like rpr_query
    '''
    query_map = {
        'get_row': get_row
    }
    
    return query_map[query_name](conn_params, get_data, post_data)


def common_query(conn_params, query_name, get_data={}):
    '''
    Run queries that needs no dynamic generation. Queries here are already stored and would
    only need to be executed on the database selected

    get_data is a django QueryDict structure
    '''
    pgsql_redundant_queries = ('template_list', 'group_list', 'user_list', 'db_list',
        'schema_list', 'db_rpr', )
    mysql_redundant_queries = ('db_list','charset_list', 'supported_engines', 'db_rpr',)

    if conn_params['dialect'] == 'postgresql' and query_name in pgsql_redundant_queries :
        # update connection db if it is different from login db
        conn_params['db'] = get_data.get('db') if get_data.get('db') else conn_params['db']
        # make query changes and mini translations
        if query_name == 'schema_list':
            if hasattr(settings, 'TT_SHOW_SYSTEM_CATALOGS'):
                query_name = 'full_schema_list' if settings.TT_SHOW_SYSTEM_CATALOGS == True else "user_schema_list"
            else: query_name = "user_schema_list" # default

        r = sa.full_query(conn_params,
            sql.stored_query(query_name, conn_params['dialect']))
        # raise Exception(r)
        return r
                
    elif conn_params['dialect'] == 'mysql' and query_name in mysql_redundant_queries :
        # this kind of queries require no special attention
        return sa.full_query(conn_params,
            sql.stored_query(query_name, conn_params['dialect']))


def get_row(conn_params, get_data={}, post_data={}):
    r = rpr_query(conn_params, 'get_single_row', get_data, post_data)
    html = u""
    if type(r) == str: return r
    for ind in range(len(r['columns'])):
        html += u'<span class="column-entry">' + unicode(r['columns'][ind]) + u'</span>'
        html += u'<br /><div class="data-entry"><code>' + unicode(r['rows'][0][ind]) + u'</code></div>'
    # replace all newlines with <br /> because html doesn't render newlines (\n) directly
    html = html.replace(u'\n', u'<br />')
    return html


def insert_row(conn_params, get_data={}, form_data={}):
    # set execution context
    conn_params['db'] = get_data['db']
    
    # format form_data ( from a form) according to the following rules
    # * add single qoutes to the variables
    # * make lists a concatenation of lists
    cols, values = [], []
    for k in form_data:
        if k in ('csrfmiddlewaretoken', 'save_changes_to'): continue
        cols.append(k)
        if type(form_data[k]) == list:
            value = u",".join(  form_data[k]  )
            values.append( fns.str_quote(value) )
        else:
            values.append( fns.str_quote(form_data[k]) )

    # generate sql insert statement
    q = u"INSERT INTO {0}{tbl} ({1}) VALUES ({2})".format(
        u'{schm}.'.format(**get_data) if conn_params['dialect'] == 'postgresql' else u'',
        u",".join(cols), u",".join(values), **get_data
        )
    
    # run query and return results
    ret = sa.short_query(conn_params, (q, ))
    if ret['status'] == 'success': ret['msg'] = 'Insertion succeeded'
    # format status messages used in flow control (javascript side)
    # replaces with space and new lines with the HTML equivalents
    ret['msg'] = '<div class="alert-message block-message {0} span8 data-entry"><code>\
{1}</code></div>'.format(
        'success' if ret['status'] == 'success' else 'error',
        ret['msg'].replace('  ', '&nbsp;&nbsp;&nbsp;').replace('\n', '<br />')
    )
    return ret


def update_row(conn_params, indexed_cols={}, get_data={}, form_data={}):
    # set execution context
    conn_params['db'] = get_data['db']
    # format form_data ( from a form) according to the following rules
    # * add single qoutes to the variables
    # * make lists a concatenation of lists
    cols, values = [], []
    for k in form_data:
        if k in (u'csrfmiddlewaretoken', u'save_changes_to'): continue
        cols.append(k)
        if type(form_data[k]) == list:
            value = u",".join(  form_data[k]  )
            values.append( fns.str_quote(value) )
        else: 
            values.append( fns.str_quote(form_data[k]) )

    # generate SET sub statment
    _l_set = []
    for i in range(len(cols)):
        short_stmt = u"=".join([cols[i], values[i]])
        _l_set.append(short_stmt)
    # generate WHERE sub statement
    _l_where = []
    for key in indexed_cols:
        short_stmt = u"=".join([ key, fns.str_quote(form_data[key]) ])
        _l_where.append(short_stmt)

    # generate full query
    q = u"UPDATE {0}{tbl} SET {set_stmts} WHERE {where_stmts}".format(
        u'{schm}.'.format(**get_data) if conn_params['dialect'] == 'postgresql' else u'',
        set_stmts = u", ".join(_l_set), where_stmts = u" AND ".join(_l_where), **get_data 
    )
    # run query and return results
    ret = sa.short_query(conn_params, (q, ))
    if ret['status'] == 'success': ret['msg'] = 'Row update succeeded'
    # format status messages used in flow control (javascript side)
    # replaces with space and new lines with the HTML equivalents
    ret['msg'] = '<div class="alert-message block-message {0} span12 data-entry"><code>\
{1}</code></div>'.format(
        'success' if ret['status'] == 'success' else 'error',
        ret['msg'].replace('  ', '&nbsp;&nbsp;&nbsp;').replace('\n', '<br />')
    )
    return ret


def do_login(request, cleaned_data):
    '''
    run query for login, store information in session if successful and then
    return the result of the login query
    '''
    # prep variables
    dict_post = {}
    for k in ['host', 'username', 'password', 'database_driver', 'connection_database']:
        dict_post[k] = cleaned_data.get(k)
    # run login query
    dict_cd = sa.model_login(dict_post)
    # load variables to session if login is succesfull
    if dict_cd['login']:
        request.session['TT_LOGIN'] = 'true'
        for k in dict_post:
            if k == 'connection_database': new_key = 'TT_DATABASE'
            elif k == 'database_driver': new_key = 'TT_DIALECT'
            else: new_key = 'TT_' + k.upper()
            request.session[new_key] = dict_post[k]
    return dict_cd


def get_home_variables(request):
    p = fns.get_conn_params(request)
    variables = {'user': p['username'], 'host': p['host']}
    variables['dialect'] = 'PostgreSQL' if p['dialect'] == 'postgresql' else 'MySQL'
    result = sa.full_query( p, sql.stored_query('variables', p['dialect']))
    if p['dialect'] == 'postgresql':
        variables['version'] = result['rows'][0]
        return variables
    elif p['dialect'] == 'mysql':
        if type(result) == dict:
            ll = result['rows']
            d = {}
            for i in range( len(ll) ):
                  d[ll[i][0]] = ll[i][1]  
            variables.update(d)
            return variables
        else:
            return fns.http_500(result)


def get_dependencies(conn_params, get_data={}): # might later be extended for objects besides tables
    '''
    logic from pgadmin3
    '''
    # get the total listing of the dependent types
    conn_params['db'] = get_data['db'] if get_data.has_key('db') else conn_params['db']
    q_1 = sql.generate_query('pgadmin_deps', conn_params['dialect'], get_data)[0]
    totl_deps = sa.full_query(conn_params, q_1)
    # columns in totl_deps are u'deptype', u'classid', u'relkind', u'adbin', u'adsrc', u'type', 
    #                           u'ownertable', u'refname', u'nspname'
    # raise Exception(totl_deps)
    columns = ['type', 'name', 'restriction',]
    
    tbl_data_rows = []
    for row in totl_deps['rows']:
        refname, typestr, depstr = '', '', ''
        # get the type of this object described in this row
        # type is the sixth column of this query
        type_ = row[5]
        if type_[0] in ('c', 's', 't'):
            continue # ununderstood types: handled internally
        elif type_[0] == 'i': typestr = 'index'
        elif type_[0] == 'S': typestr = 'sequence'
        elif type_[0] == 'v': typestr = 'view'
        elif type_[0] == 'x': typestr = 'exttable'
        elif type_[0] == 'p': typestr = 'function'
        elif type_[0] == 'n': typestr = 'schema'
        elif type_[0] == 'y': typestr = 'type'
        elif type_[0] == 'T': typestr = 'trigger'
        elif type_[0] == 'l': typestr = 'language'
        elif type_[0] == 'R':
            pass
        elif type_[0] == 'C':
            if type_[1] == 'c': typestr = 'check'
            elif type_[1] == 'f': 
                refname = row[6] +'.'
                typestr = 'foreign key'
            elif type_[1] == 'u': typestr = 'unique'
            elif type_[1] == 'p': typestr = 'primary key'
            elif type_[1] == 'x': typestr = 'exclude'
        elif type_[0] == 'A':
            if row[3] != None and row[3].startswith("{FUNCEXPR"):
                typestr = 'function'
                refname = row[4] # adbin
        # complete refname
        # appends the name of the foreign key if the type of object is a foreign key
        # function has the refname already set
        refname = refname + row[7] # refname
        # deptype is the first column of this query
        deptype = row[0]
        if deptype == 'i': depstr = 'internal'
        elif deptype == 'a': depstr = 'auto'
        elif deptype == 'n': depstr = 'normal'
        elif deptype == 'p': depstr = 'pin'

        tbl_data_rows.append([typestr, refname, depstr])

    return {'count': totl_deps['count'], 'columns': columns, 
        'rows': tbl_data_rows
    }


def create_column(conn_params, get_data={}, form_data={}):
    # fetch queries
    queries = sql.get_column_sql(conn_params['dialect'], get_data, form_data)
    ret = sa.short_query(conn_params, queries)
    if ret['status'] == 'success': ret['msg'] = 'column creation succesfull'
    # format status messages used in flow control (javascript side)
    # replaces with space and new lines with the HTML equivalents
    ret['msg'] = '<div class="alert-message block-message {0} data-entry"><code>\
{1}</code></div>'.format(
        'success' if ret['status'] == 'success' else 'error',
        ret['msg'].replace('  ', '&nbsp;&nbsp;&nbsp;').replace('\n', '<br />')
    )
    return ret


def get_constraints(conn_params, query_type, get_data={}, form_data={}):
    # first face the simple guy
    if conn_params['dialect'] == 'mysql':
        r = sa.full_query(conn_params,
            sql.generate_query(query_type, conn_params['dialect'], get_data)[0])
        return r

    # this sequence of code would be repeated often
    def get_cols_with_post_as_dict(get_data):
        # query for column name associated with its ordinal position. 
        sql_stmt = sql.generate_query('column_assoc', conn_params['dialect'], get_data)[0]
        cols_with_pos = sa.full_query(conn_params, sql_stmt)
        # transform to dict for quick and easy indexing and retrieval
        cols_with_pos = dict(cols_with_pos['rows'])
        return cols_with_pos


    # get raw constrainsts description
    sql_stmt = sql.generate_query('constraints', conn_params['dialect'], get_data)[0]
    con_desc = sa.full_query(conn_params, sql_stmt,);
    # char to constraint type mapping as written in PostgreSQL documentation
    char_constraint_map = {
        'c': 'CHECK',
        'f': 'FOREIGN KEY',
        'p': 'PRIMARY KEY',
        'u': 'UNIQUE',
    }

    columns = ['type', 'columns', 'description', 'name',]
    rows = []
    cols_with_pos = get_cols_with_post_as_dict(get_data)

    for row in con_desc['rows']:
        # contype 0, conname 1, conkey 2, confkey 3, relname 4, consrc 5
        contype, conname, conkey, confkey, relname, consrc = row
        # any contype not in the mapping above is not yet supported
        if not char_constraint_map.has_key(contype): continue
        desc = '' # starts empty
        constrained_columns = ", ".join( [cols_with_pos[i] for i in conkey] )
        type_ = char_constraint_map[contype]
        # if this query is a foreign key translate the column names
        if contype == 'c':
            desc = consrc
        if contype == 'f':
            if relname != get_data.get('tbl'): # we need to get another columns with pos
                get_data['tbl'] = relname
                fr_cols_with_pos = get_cols_with_post_as_dict(get_data)
            else: fr_cols_with_pos = cols_with_pos

            referred_columns = [ fr_cols_with_pos[i] for i in confkey]
            desc = relname + ":" + ", ".join(referred_columns)

        # done
        rows.append([ type_, constrained_columns, desc, conname])

    return {'columns': columns, 'rows': rows, 'count': len(con_desc['rows'])}


def get_table_names(): pass


def run_tbl_operations(conn_params, form_type, get_data={}, post_data={}):
    # generate / derive queries to be run
    queries, msg = [], ''
    if form_type == 'tbl_edit_form':
        queries, msg = sql.alter_table(conn_params['dialect'], get_data, post_data)
    elif form_type == 'tbl_vacuum_form':
        queries = sql.pg_vacuum_stmt(get_data, post_data)
    else:
        # implemented queries: analyze table and reindex table
        # only the pg dialect
        queries = sql.generate_query(form_type, conn_params['dialect'], get_data)

    # execute queries and return formatted status messages
    if form_type == 'tbl_edit_form':
        ret = sa.short_query(conn_params, queries)
    else: ret = sa.execute_outside_transaction(conn_params, queries)

    if ret['status'] == 'success':
        if form_type == 'tbl_edit_form': ret['msg'] = msg + ' change succesfull'
        else:
            msg = '{command} operation ran succesfully'
            if form_type == 'tbl_vacuum_form': com = 'VACUUM'
            elif form_type == 'analyze_table': com = 'ANALYZE'
            elif form_type == 'reindex_table': com = 'REINDEX'
            ret['msg'] = msg.format(command=com)

    ret['msg'] = '<p class="query-msg {status}">{msg}</p>'.format(
            status = 'error' if ret['status'] == 'error' else 'success',
            msg = ret['msg']
        )
    return ret

