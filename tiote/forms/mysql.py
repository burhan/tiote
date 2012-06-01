from django import forms
from django.core import validators
from django.utils.datastructures import SortedDict
from common import *

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
        


class mysqlTableForm(forms.BaseForm):
    
    def __init__(self, engines=None, charsets=None, edit=False, column_count=1, column_form=False,
        existing_tables = None, existing_columns = None, **kwargs):
        f = SortedDict()
        engine_list = []
        default_engine = ''
        for tup in engines:
            engine_list.append((tup[0],))
            if tup[1] == 'DEFAULT':
                default_engine = tup[0]
        if edit is False:
            f['name'] = forms.CharField(widget=forms.TextInput(attrs={'class':'required'}))
            f['charset'] = forms.ChoiceField(
                choices = fns.make_choices(charsets),
                initial='latin1'
            )
            f['engine'] = forms.ChoiceField(
                required = False, 
                choices = fns.make_choices( engine_list ),
                initial = default_engine
            )
        # variable amount of column_count
        # field label's are directly tied to the corresponding template
        for i in range( column_count ):
            sfx = '_' + str(i)
            f['name'+sfx] = forms.CharField(
                widget=forms.TextInput(attrs={'class':'required'}),
                label = 'name')
            f['type'+sfx] = forms.ChoiceField(
                choices = fns.make_choices(mysql_types),
                widget = forms.Select(attrs={'class':'required needs:values:set|enum select_requires:values'
                    +sfx+':set|enum select_requires:size'+sfx+':varchar'}),
                initial = 'varchar',
                label = 'type',
            )
            f['values'+sfx] = forms.CharField(
                label = 'values', required = False, 
                help_text="Enter in the format: ('yes','false')",
            )
            f['size'+sfx] = forms.IntegerField(
                widget=forms.TextInput(attrs={'class':'validate-integer'}),
                label = 'size', required=False, )
            f['key'+sfx] = forms.ChoiceField(
                required = False,
                widget = forms.Select(attrs={'class':'even'}),
                choices = fns.make_choices(mysql_key_choices),
                label = 'key',
            )
            f['default'+sfx] = forms.CharField(
                required = False,
                label = 'default',
                widget=forms.TextInput
            )
            f['charset'+sfx] = forms.ChoiceField(
                choices = fns.make_choices(charsets), 
                initial='latin1',
                label = 'charset',
                widget=forms.Select(attrs={'class':'required'})
            )
            f['other'+sfx] = forms.MultipleChoiceField(
                choices = fns.make_choices(mysql_other_choices, True),
                widget = forms.CheckboxSelectMultiple(attrs={'class':'occupy'}),
                required = False,
                label = 'other',
            )
        if column_form:
            f['insert_position'] = forms.ChoiceField(
                choices = fns.make_choices(['at the end of the table', 'at the beginning'], True)
                    + fns.make_choices(existing_columns,False,'--------','after'),
                label = 'insert this column',
                initial = 'at the end of the table',
                widget = forms.Select(attrs={'class':'required'}),
            )
        # complete form creation process
        self.base_fields = f
        forms.BaseForm.__init__(self, **kwargs)

