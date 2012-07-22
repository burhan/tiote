import hashlib, random
from django.http import HttpResponse, Http404
from django.contrib.sessions.models import Session
from django.template import loader, RequestContext, Template

# a list of all the abbreviations in use
_abbr = {
    'sctn': 'section',
    'tbl': 'table',
    'tbls': 'tables',
    'v': 'view',
    'schm': 'schema',
    'idxs': 'indexes',
    'cols': 'columns',
    'seq': 'sequence',
    'seqs': 'sequences',
    'q': 'query',
    'ov': 'overview',
    'struct': 'structure',
    'hm': 'home',
    'ins': 'insert',
    'dbs': 'databases',
    'deps': 'dependents',
    'fkeys': 'foreign keys',
    'cons': 'constraints',
    'ops': 'operations',
    'pg': 'page',
}

# returns page templates for each view
def skeleton(which, section=None ):
    s = section+'/' if section != None else ''
    ss = s+'tt_' + which + '.html'
    return loader.get_template(s+'tt_' + which + '.html')


def check_login(request):
    return request.session.get('TT_LOGIN', '')


def set_ajax_key(request):
    if request.session.get('ajaxKey', False):
        return

    sessid = hashlib.md5( str(random.random()) ).hexdigest()
    try: # some environments eg. GAE doesn't have this
        d = request.META['PWD']
    except KeyError:
        d = ""
    request.session['ajaxKey'] = hashlib.md5(sessid + d).hexdigest()[0:10]


def validateAjaxRequest(request):
    if request.GET.get('ajaxKey', False) and request.GET.get('ajaxKey', False) == request.session.get('ajaxKey',''):
        return True
    else:
        return False

    
def make_choices(choices, begin_empty=False, begin_value='', append_label=''):
    '''
    Duplicate each item in choices to make a (stored_name, display_name) pair.

    Prepends the return sequence with an empty pair if begin_empty is True.

    Or could accept and optional begin_value to be the prepended pair as explained above.
    '''
    ret = [] if begin_empty else [('',
                        begin_value if begin_value else ''),]
    for i in range( len(choices) ):
        if type(choices[i]) == str or type(choices[i])== int:
            ret.append( (choices[i], choices[i]) )
        elif type(choices[i]) == tuple or type(choices[i]) == list:
            ret.append( (choices[i][0],
                append_label+' '+choices[i][0] if append_label else choices[i][0]) )
    return ret

def site_proc(request):
    # abbreviations is splitted into arrays so that they can support 
    # - searching both by keys and abbrevs_values
    return {
        'ajaxKey': request.session.get('ajaxKey',''),
        'abbrevs_keys': _abbr.keys(),
        'abbrevs_values': _abbr.values(),
        'dialect': get_conn_params(request)['dialect'],
    }

def http_500(msg=''):
    response = HttpResponse(msg)
    response.status_code = '500'
    return response
    
def form_errors(request, form):
    template = skeleton('form-errors')
    context = RequestContext(request, {'form':form}, 
        [site_proc]
    )
    h = HttpResponse(template.render(context))
    h.set_cookie('tt_formContainsErrors','true')
    return h
    
def get_conditions(l):
    conditions = []
    for i in range( len(l) ):
        ll = l[i].strip().split('/i/AND/o/')
        d = {}
        for ii in range( len(ll) ):
            lll = ll[ii].strip().split('=')
            d[ lll[0].lower() ] = lll[1].lower()
        conditions.append(d)
    return conditions


def response_shortcut(request, template = False, extra_vars=False ):
    '''
    A view response shortcut which finds the required template by some concatenating and then
    process the return object with a RequestContext and some optional context as specified in 
    the ``extra_vars`` parameter
    '''
    # extra_vars are more context variables
    template = skeleton(template) if template else skeleton(request.GET['v'], request.GET['sctn'])
    context = RequestContext(request, {
        }, [site_proc]
    )
    if extra_vars:
        context.update(extra_vars)
    h =  HttpResponse(template.render(context))
    if template == 'form_errors':
        h.set_cookie('tt_formContainsErrors','true')
    return h


def get_conn_params(request, update_db=False):
    data = {}
    for k in ['host', 'username', 'password', 'dialect']:
        data[k] = request.session.get('TT_' + k.upper())
    if request.session.get('TT_DATABASE'):
        data['db'] = request.session.get('TT_DATABASE')
    else:
        data['db'] = '' if data['dialect'] =='mysql' else 'postgres'
    # get the new 'db' from the request.GET and update the 'db' key of the
    # - returned dict only if udpate_db is true
    if update_db and request.GET.get('db'):
        data['db'] = request.GET.get('db')
    return data


def qd(query_dict):
    '''
    ugly function
    returns an object instead of a list as the norms of QuerySets
    '''
    return dict((key, query_dict.get(key)) for key in query_dict)


# render the given template with a RequestContext(main reason)
def render_template(request, template, context= {}, is_file=False):
    '''
    Helper function which uses ``request`` to get the RequestContext which is used 
    to provide extras context and renders the given template.
    '''
    _context = RequestContext(request, {}, [site_proc])
    if len(context) > 0: _context.update(context)
    t = loader.get_template(template) if is_file else Template(template) 
    return t.render(_context)


def parse_indexes_query(tbl_indexes, needed_indexes=None):
    '''
    Creates a dict mapping with key as name of the column which maps to a list
    which contains all the indexes on the said key. 

    Returns a Bucket dict (like django QuerySets)

    e.g.
        {
            'id': ['PRIMARY KEY'],
            'NAME': ['UNIQUE', 'FOREIGN KEY'],
        }
    '''
    _dict = {}

    for row in tbl_indexes:
        if needed_indexes != None and row[2] not in needed_indexes: 
            continue
        if _dict.has_key(row[0]): 
            _dict[ row[0] ].append( row[2] )
        else: 
            _dict[ row[0] ] = [ row[2] ]
    return _dict


def quote(obj):
    '''
    return a single quoted version of the passed in string obj
    '''
    if type(obj) == str:
        return "'%s'" % obj
    elif type(obj) == unicode:
        return u"'%s'" % obj
    else:
        return obj

def str_quote(obj):
    ''' always returns a unicode object '''
    return unicode( quote(obj))

def where_frm_conditns(conditns):
    where_stmts = []
    for conditn in conditns:
        where_stmt, last_key = "", conditn.keys()[-1]
        for k, v in conditn.iteritems():
            where_stmt += "{key}={value}".format(key=k, value=quote(v))
            if k != last_key: where_stmt + "; "
            where_stmts.append(where_stmt)
    return where_stmts

