from django import forms
from django.core import validators
from django.utils.datastructures import SortedDict
from common import *
from tiote.utils import *


class pgDbForm(forms.BaseForm):
    
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


class pgUserForm(forms.BaseForm):
    
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



class pgSequenceForm(forms.Form):
    
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



class pgTableEditForm(forms.BaseForm):

    def __init__(self, tbl_name=None, tbl_schema=None, 
            # tbl_owner = None,
            users=[], schemas=[], tbl_comment='', tablespace=[], **kwargs):

        if tbl_name == None or tbl_schema == None:
            raise TypeError('tbl_name or tbl_schema is required')

        f = SortedDict()
        f['name'] = forms.CharField(
                max_length= 64,
                widget= forms.TextInput(attrs={'class':'required'}),
                initial = tbl_name,
            )

        # roles and users is not yet implemented in tiote
        # f['owner'] = forms.ChoiceField(
        #         choices = fns.make_choices(users, begin_empty=True),
        #         initial = tbl_owner
        #     )

        f['schema'] = forms.ChoiceField(
                choices = fns.make_choices(schemas, begin_empty=True),
                initial = tbl_schema
            )

        # comment is not yet in use in tiote
        # f['comment'] = forms.CharField(required=False, 
        #         widget = forms.Textarea(attrs={'cols':0, 'rows':0})
        #     )

        self.base_fields = f
        super(pgTableEditForm, self).__init__(**kwargs)


class TableVacuumForm(forms.Form):

    full = forms.BooleanField(required=False)
    analyze = forms.BooleanField(required=False)
    freeze = forms.BooleanField(required=False)


