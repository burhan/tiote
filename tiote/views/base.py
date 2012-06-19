'''
base classes for tiote views
'''
from django.http import HttpResponse
from django.views.generic import View
from tiote.utils import *


class GETOnlyView(View):
    '''
    for every type of HTTP request return a get request
    '''
    def head(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class BareTableView(View):
    '''
    basic assumption here: all the variables for init have been already been attached
    to the self pointer by the base constructor

    self.object_name
    self.tbl_data
    self.show_tbl_optns
    self.tbl_optn_type
    self.tbl_props
    self.empty_err_msg
    '''
    def _init_vars(self, request):
        ''' init variables '''
        self.conn_params = fns.get_conn_params(request)
        self.static_addr = fns.render_template(request, '{{STATIC_URL}}')
    
    def get(self, request, *args, **kwargs):
        self._init_vars(request)
        
        if self.tbl_data['count'] < 1:
            return '<div class="undefined">[%s]</div>' % self.empty_err_msg

        # build table properties
        if not hasattr(self, 'tbl_props'): self.tbl_props = {}
        if self.tbl_data.has_key('keys') and self.tbl_data.get('keys') != None:
            self.tbl_props['keys'] = self.tbl_data['keys']['rows']
        self.tbl_props['count'] = self.tbl_data['count'],

        html_table = htm.HtmlTable(
            static_addr = self.static_addr,
            columns = self.tbl_data['columns'],
            rows = self.tbl_data['rows'],
            props = self.tbl_props,
            attribs = getattr(self, 'tbl_attribs', {}),
            store = getattr(self, 'tbl_store',{}),
            assoc_order = getattr(self, 'tbl_assoc_order', None),
            columns_desc = getattr(self, 'columns_desc', []),
            )

        if hasattr(self, 'show_tbl_optns') and getattr(self, 'show_tbl_optns', False):
            tbl_optns_html = htm.table_options(
                getattr(self, 'tbl_optn_type', 'data'),
                with_keys = self.tbl_props.has_key('keys') and len(self.tbl_props['keys'])
                )
        else: tbl_optns_html = ''

        ret_str = tbl_optns_html + html_table.to_element()

        return ret_str


class TableView(BareTableView, GETOnlyView):
    '''
    Wraps BareTableView to return a HttpResponse as opposed to a string.
    '''

    def get(self, request, *args, **kwargs):
        return HttpResponse( super(TableView, self).get(request, *args, **kwargs))


class CompositeTableView(BareTableView):
    '''
    Returns a tab page with only one html_table and pointers(links) to others

    Assumed keyword args
    self.subv : current half page
    self.subnav_list
    self.url_prfx
    '''

    def get(self, request, *args, **kwargs):
        singl_tbl_view = super(CompositeTableView, self).get(request, *args, **kwargs)

        if not hasattr(self, 'subnav_list'):
            raise Exception('subnav_list must be passed into the constructor')

        if not hasattr(self, "subv_key"):
            self.subv_key = 'subv'

        if len(self.subnav_list) <= 1:
            # no need for tabbing
            return HttpResponse(singl_tbl_view)
        
        _l = []
        for _it in self.subnav_list:
            _l.append('<li{0}><a href="{1}">{2}<span>|</span></a></li>'.format(
                ' class="active"' if _it == self.subv else '',
                '#%s&%s=%s' % (self.url_prfx, self.subv_key, _it),
                fns._abbr[_it] if fns._abbr.has_key(_it) else _it,
                )
            )

        subnav_str = '<div style="margin-bottom:-5px;"><ul class="subnav">{0}</ul></div>'.format(''.join(_l))
        ret_str = subnav_str + singl_tbl_view
        return HttpResponse(ret_str)


class BareFormView(View): pass

class FormView(BareFormView):

    def get(self, request, *args, **kwargs):
        pass
