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


