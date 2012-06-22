from django import forms
from django.core import validators
from django.utils.datastructures import SortedDict
from common import *
from tiote.utils import *

# New Database Form
class mysqlDbForm(forms.Form):
    def __init__(self, templates=None, users=None, charsets=None, **kwargs):
        f = SortedDict()
        f['name'] = forms.CharField(widget=forms.TextInput(attrs={'class':'required'}))
        f['charset'] = forms.ChoiceField(
            choices = fns.make_choices(charsets),
            initial = 'latin1'
        )
        self.base_fields = f
        forms.BaseForm.__init__(self, **kwargs)


#New Role/User Form
class mysqlUserForm(forms.BaseForm):
    
    def __init__(self, dbs = None, groups=None, **kwargs):
        f = SortedDict()
            
        f['host'] = forms.CharField(
            widget=forms.TextInput(attrs={'class':'required '}),
            initial='localhost',
        )
        f['username'] = forms.CharField(
            widget=forms.TextInput(attrs={'class':'required '})
        )
        f['password'] = forms.CharField(
            widget=forms.PasswordInput(attrs={'class':''}),
            required = False
        )    
        f['access'] = forms.ChoiceField(
            choices = (('all', 'All Databases'),('select', 'Selected Databases'),),
            widget = forms.RadioSelect(attrs={'class':'addevnt hide_1'}),
            label = 'Allow access to ',
        )
    
        f['select_databases'] = forms.MultipleChoiceField(
            required = False,
            widget = forms.CheckboxSelectMultiple(attrs={'class':'retouch'}),
            choices = fns.make_choices(dbs, True),
        )
        f['privileges'] = forms.ChoiceField(
            choices = (('all', 'All Privileges'),('select','Selected Privedges'),),
            widget = forms.RadioSelect(attrs={'class':'addevnt hide_2'})
        )
    
        f['user_privileges'] = forms.MultipleChoiceField(
            required = False,
            widget = forms.CheckboxSelectMultiple(attrs={'class':'privileges'}),
            choices = fns.make_choices(user_privilege_choices, True),
        )
        f['administrator_privileges'] = forms.MultipleChoiceField(
            required = False,
            choices = fns.make_choices(admin_privilege_choices, True) ,
            widget = forms.CheckboxSelectMultiple(attrs={'class':'privileges'}),
        )
        f['options'] = forms.MultipleChoiceField(
            choices = (('GRANT OPTION','Grant Option'),),
            widget = forms.CheckboxSelectMultiple,
            required = False,
        )
        
        self.base_fields = f
        forms.BaseForm.__init__(self, **kwargs)
        

class mysqlTableEditForm(forms.BaseForm):

    def __init__(self, tbl_name=None, current_charset=None, charsets=[], **kwargs):
        f = SortedDict()

        f['name'] = forms.CharField(
                widget = forms.TextInput(attrs={'class':'required'}),
                initial = tbl_name,
            )

        f['charset'] = forms.ChoiceField(
                choices = fns.make_choices(charsets, begin_empty=True),
                # initial = current_charset,
            )

        self.base_fields = f
        super(mysqlTableEditForm, self).__init__(**kwargs)


