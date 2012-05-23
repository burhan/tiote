'''
base classes for tiote views
'''
from django.http import HttpResponse
from django.views.generic import View
from tiote.utils import *

class FormView():
    
    def __init__(self, form, post_callback, form_template=None,):
        pass



class PageView():
    pass


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


class TableView(View):
    '''
    basic assumption here: all the variables for init have been already been attached
    to the self pointer by the base constructor

    self.object_name
    self.tbl_data
    self.show_tbl_optns
    self.tbl_optn_type
    self.tbl_props
    '''
    def _init_vars(self, request):
        ''' init variables '''
        self.conn_params = fns.get_conn_params(request)
        self.static_addr = fns.render_template(request, '{{STATIC_URL}}')
    
    def get(self, request, *args, **kwargs):
        self._init_vars(request)
        
        if self.tbl_data['count'] < 1:
            return HttpResponse('<div class="undefined">[This table contains no entry]</div>')

        # build table properties
        if not hasattr(self, 'tbl_attribs'): self.tbl_attribs = {}
        if not hasattr(self, 'tbl_props'): self.tbl_props = {}
        if self.tbl_data.has_key('keys'):
            self.tbl_props['keys'] = self.tbl_data['keys']['rows']
        self.tbl_props['count'] = self.tbl_data['count'],

        html_table = htm.HtmlTable(
            static_addr = self.static_addr,
            columns = self.tbl_data['columns'],
            rows = self.tbl_data['rows'],
            props = self.tbl_props,
            attribs = self.tbl_attribs,
            )

        if self.show_tbl_optns:
            tbl_optns_html = htm.table_options(
                getattr(self, 'tbl_optn_type', 'data'),
                with_keys = self.tbl_props.has_key('keys')
                )

        ret_str = tbl_optns_html + html_table.to_element()

        return HttpResponse(ret_str)