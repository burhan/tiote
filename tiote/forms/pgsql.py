from django import forms
from django.core import validators
from django.utils.datastructures import SortedDict
from common import *


class pgsqlDbForm(forms.BaseForm):
    
    def __init__(self, templates=None, users=None, charsets=None, **kwargs):
        f = SortedDict()
        
        f['name'] = forms.CharField(widget=forms.TextInput(attrs={'class':'required'}))
        f['encoding'] = forms.ChoiceField(
            choices = fns.make_choices(pgsql_encoding),
            initial = 'UTF8',
            )
        f['template'] = forms.ChoiceField(
            choices = fns.make_choices(templates),
            required = False,
        )
        f['owner'] = forms.ChoiceField( choices = fns.make_choices(users) ,
            required = False, )
        
        self.base_fields = f
        forms.BaseForm.__init__(self, **kwargs)


class pgsqlUserForm(forms.BaseForm):
    
    def __init__(self, groups=None, dbs=None, **kwargs):
        f = SortedDict()
        f['role_name'] = forms.CharField(
            widget = forms.TextInput(attrs={'class':'required'})
            )
        f['can_login'] = forms.CharField(
            widget = forms.CheckboxInput
            )
        f['password'] = forms.CharField(
            widget = forms.PasswordInput,
            required = False
            )
        f['valid_until'] = forms.DateTimeField(
            widget = forms.TextInput(attrs={}),
            required = False)
        f['connection_limit'] = forms.IntegerField(
            widget=forms.TextInput(attrs={'class':'validate-integer'}),
            required = False)
#        f['comment'] = forms.CharField(
#            widget = forms.Textarea(attrs={'cols':'', 'rows':''}),
#            required = False)
        f['role_privileges'] = forms.MultipleChoiceField(
            required = False, widget = forms.CheckboxSelectMultiple,
            choices = fns.make_choices(pgsql_privileges_choices, True) 
        )
        if groups:
            f['group_membership'] = forms.MultipleChoiceField(
                choices = fns.make_choices(groups, True), required = False,
                widget = forms.CheckboxSelectMultiple,)
        
        self.base_fields = f
        forms.BaseForm.__init__(self, **kwargs)


# table and columns creation form
class pgsqlTableForm(forms.BaseForm):
    
    def __init__(self, engines=None, charsets=None, edit=False, column_count=1, column_form=False,
        existing_tables = None, existing_columns = None, **kwargs):
        f = SortedDict()
        wdg = forms.Select(attrs={}) if existing_tables else forms.Select
        
        if edit is False:
            f['name'] = forms.CharField(widget=forms.TextInput(attrs={'class':'required'}))
            f['of_type'] = forms.ChoiceField(
                choices = fns.make_choices(existing_tables),
                required = False, widget = wdg
                )
            f['inherit'] = forms.ChoiceField(
                choices = fns.make_choices(existing_tables),
                required = False, widget = wdg
                )
        # variable number of columns
        for i in range( column_count ):
            fi = str(i)
            f['name_'+fi] = forms.CharField(
                widget=forms.TextInput(attrs={'class':'required'}),
                label = 'name')
            f['type_'+fi] = forms.ChoiceField(
                label = 'type',
                choices = fns.make_choices(pgsql_types),
                widget = forms.Select(attrs={'class':'required'}),
                )
            f['length_'+fi] = forms.IntegerField(
                widget=forms.TextInput(attrs={'class':'validate-integer'}),
                label = 'length', required=False, )
            f['key_'+fi] = forms.ChoiceField(
                required = False,
                widget = forms.Select(attrs={'class':'even needs:foreign-fields:foreign'
                        +' select_requires:references_'+fi+'|column_'+fi+':foreign'}),
                choices = fns.make_choices(pgsql_key_choices),
                label = 'key',
            )
            f['references_'+fi] = forms.ChoiceField(
                required= False, label = 'references',
                choices = fns.make_choices(existing_tables),
                widget = forms.Select()
                )
            f['column_'+fi] = forms.ChoiceField(
                required = False, label = 'column',
                )
            f['on_update_'+fi] = forms.ChoiceField(
                required= False, label = 'on update',
                choices = fns.make_choices(foreign_key_action_choices, True)
            )
            f['on_delete_'+fi] = forms.ChoiceField(
                required = False, label = 'on delete',
                choices = fns.make_choices(foreign_key_action_choices, True)
            )
            f['default_'+fi] = forms.CharField(
                required = False,
                label = 'default',
                widget=forms.TextInput
            )
            f['other_'+fi] = forms.MultipleChoiceField(
                label = 'other', required = False,
                widget = forms.CheckboxSelectMultiple(),
                choices = fns.make_choices(['not null'], True))
        if column_form:
            f['insert_position'] = forms.ChoiceField(
                choices = fns.make_choices(['at the end of the table', 'at the beginning'], True)
                    + fns.make_choices(existing_columns,False,'--------','after'),
                label = 'insert this column',
                initial = 'at the end of the table',
                widget = forms.Select(attrs={'class':'required'}),
            )
        self.base_fields = f
        forms.BaseForm.__init__(self, **kwargs)


    
class pgsqlSequenceForm(forms.Form):
    
    name = forms.CharField(
        widget=forms.TextInput(attrs={'class':'required'})
    )
    incremented_by = forms.IntegerField(
        required=False, 
        widget = forms.TextInput(attrs={'class':'validate-integer'})
    )
    min_value = forms.IntegerField(
        required=False, 
        widget = forms.TextInput(attrs={'class':'validate-integer'})
    )
    max_value = forms.IntegerField(
        required=False, 
        widget = forms.TextInput(attrs={'class':'validate-integer'})
    )
    start_value = forms.IntegerField(
        required = False, 
        widget = forms.TextInput(attrs={'class':'validate-integer'})
    )
    cache_value = forms.IntegerField(
        required =False, 
        widget = forms.TextInput(attrs={'class':'validate-integer'})
    )
    can_cycle = forms.ChoiceField(
        label = 'Can cycle?', required = False,
        widget = forms.CheckboxInput()
    )


