from django import forms
from django.core import validators
from django.utils.datastructures import SortedDict
from django.utils.safestring import SafeUnicode

from tiote.utils import *
# children modules (in files) of this module
from common import *
from pgforms import *
from mysqlforms import *


class InsertForm(forms.BaseForm):
    '''
    Dynamically created form which generates its fields along with the fields' options
    from its parameters. 

    Does not make use of metaclasses so it subclasses forms.BaseForm directly.

    It loops through the parameter ``tbl_struct``(the structure of a table) and then generates
    fiels which would fit the description of respective columns

    It also treats some fields specially as defined in ``tbl_indexes`` and the form's ``dialect``
    '''

    def __init__(self, dialect, tbl_struct, tbl_indexes=(), **kwargs):
# keys = ['column','type','null','default','character_maximum_length','numeric_precision', 'extra','column_type']
        f = SortedDict()
        # dict to increase performance
        indexed_cols = fns.parse_indexes_query(tbl_indexes)
        
        # determing type of form fields for each column
        for row in tbl_struct['rows']:
            _classes = []

            if row[1] in ('character varying', 'varchar','character', 'char'):
                f[row[0]] = forms.CharField()
                # if row[4]: f[row[0]].max_length = row[4] #max_length

            elif row[1] in ('varbinary', 'bit', 'bit varying',):
                f[row[0]] = forms.CharField()
                # if row[4]: f[row[0]].max_length = row[4] #max_length

            elif row[1] in ('text', 'tinytext', 'mediumtext', 'longtext', ):
                f[row[0]] = forms.CharField(widget=forms.Textarea(attrs={'cols':'', 'rows':''}))
                # if row[4]: f[row[0]].max_length = row[4] #max_length

            elif row[1] in ('boolean', ):
                f[row[0]] = forms.BooleanField(
                    required=False # so it can accept 'True' and 'False', not just 'True'
                    )

            elif row[1] in ('tinyint', 'smallint', 'mediumint', 'int', 'bigint','integer',):
                f[row[0]] = forms.IntegerField()
                # if row[5]: f[row[0]].validators.append(validators.MaxLengthValidator(row[5]))
                _classes.append('validate-integer')
                
            elif row[1] in ('real', 'double', 'float', 'decimal', 'numeric', 'double precision'):
                f[row[0]] = forms.FloatField()
                # if row[5]: f[row[0]].validators.append(validators.MaxLengthValidator(row[5]))
                _classes.append('validate-numeric')

            elif row[1] in ('decimal', 'numeric', 'money',):
                f[row[0]] = forms.DecimalField()
                # if row[5]: f[row[0]].validators.append(validators.MaxLengthValidator(row[5]))
                _classes.append('validate-numeric')

            elif row[1] in ('date',):
                f[row[0]] = forms.DateField()
                _classes.append('validate-date')

            elif row[1] in ('datetime', 'time','time with time zone','timestamp', 'timestamp with time zone',):
                # no longer used a python field (date, datetime) because
                # - of error generated when submitting fields which
                # - are populated from the database
                f[row[0]] = forms.CharField() 
                
            elif row[1] == 'set':
                f[row[0]] = forms.MultipleChoiceField(widget=tt_CheckboxSelectMultiple())
                # parse the field description to list with all the unnecssary quotes removed
                choices = row[len(row)-1].replace("set(", "").replace(")","")
                choices = choices.replace("'", "").split(",")
                f[row[0]].choices = fns.make_choices(choices, True) 

            elif row[1] == 'enum':
                f[row[0]] = forms.ChoiceField()
                # parse the field description to list with all the unnecssary quotes removed
                choices = row[len(row)-1].replace("enum(", "").replace("\"","").replace(")","")
                choices = choices.replace("'", "").split(",")
                f[row[0]].choices = fns.make_choices(choices, False) 
            
            # any field not currently understood (PostgreSQL makes use of a lot of user defined fields
                # which is difficult to keep track of)
            else: f[row[0]] = forms.CharField(widget=forms.Textarea(attrs={'cols':'', 'rows':''}))

            #required fields
            if row[2].lower() == 'no' or row[2] == False:
                # the field row[2] is required
                _classes.append("required")
                # the option  above must be the last assignment to _classes because it's index
                # - must be the last one for the next lines of logic to work
            else:
                f[row[0]].required = False
                
            # options common to all fields
            # help_text
            _il = [ row[len(row) - 1], ]
            if dialect == 'mysql': _il.append(row[len(row) -2 ])
            f[row[0]].help_text =  " ".join(_il)
            if row[3]: f[row[0]].default = row[3] #default
            
            # work with indexes
            if indexed_cols.has_key( row[0] ):
                if dialect == 'mysql' and indexed_cols[ row[0] ].count("PRIMARY KEY"):
                    # make an indexed column with auto_increment flag not required (MySQL)
                    if row[len(row) - 2].count('auto_increment') > 0: 
                        if _classes.count('required') > 0: _classes.pop()
                        f[ row[0] ].required = False

            # width of the fields
            if type(f[row[0]].widget) not in (forms.CheckboxSelectMultiple, tt_CheckboxSelectMultiple,):
                _classes.append("span6")
            # add the attribute classes                
            if f[row[0]].widget.attrs.has_key('class'):
                f[row[0]].widget.attrs['class'] += " ".join(_classes)
            else:
                f[row[0]].widget.attrs.update({'class':" ".join(_classes)})


        self.base_fields = f
        forms.BaseForm.__init__(self, **kwargs)


class EditForm(InsertForm):
    '''
    Subclasses InsertForm to include the dynamic property of InsertForm as well as to 
    add and option that specifies if the request would be for a new row or would be 
    an update for that row
    '''

    def __init__(self, dialect, tbl_struct, tbl_indexes=(), **kwargs):
        InsertForm.__init__(self, dialect, tbl_struct, tbl_indexes, **kwargs)

        # working with self.fields attribute because this is an instance of InsertForm
        # - and not a whole form class definition
        self.fields['save_changes_to'] = forms.ChoiceField(
            label = 'save changes to',
            choices = (('update_row', 'Same row (UPDATE statment)',),
                ('insert_row', 'Another row (INSERT statement)')
            ), 
            initial = 'update_row',
            widget = forms.RadioSelect(attrs={'class':'inputs-list'}, renderer = tt_RadioFieldRenderer)
        )


    
class LoginForm(forms.BaseForm):
    
    def __init__(self, templates=None, choices="a", charsets=None, **kwargs):
        f = SortedDict()
        # choices = "a" || all choices
        # choices = "m" || mysql dialect
        # , 
        # choices = "p" || postgresql dialect
        database_choices = [ ('', 'select database driver'),]
        if choices == "p" or choices == "a":
            database_choices.append(('postgresql', 'PostgreSQL'))
        if choices == "m" or choices == "a":
            database_choices.append(('mysql', 'MySQL'))
        f['host'] = forms.CharField(
            initial = 'localhost', widget=forms.TextInput(attrs=({'class':'required'}))
        )
        f['username'] = forms.CharField(
            widget=forms.TextInput(attrs=({'class':'required'}))
        )
        f['password'] = forms.CharField(
            widget = forms.PasswordInput,
            required = False,
        )
        f['database_driver'] = forms.ChoiceField(
            choices = database_choices,
            widget = forms.Select(attrs={
    #            'class':'select_requires:connection_database:postgresql'
                'class':'required'
                    }
            ),
        )
        f['connection_database'] = forms.CharField(
            required=False, 
            help_text='Optional but needed if the PostgreSQL installation does not include the default `postgres` database'
        )
        self.base_fields = f
        forms.BaseForm.__init__(self, **kwargs)



class QueryForm(forms.Form):
    query = forms.CharField(label = u"Enter your query:", 
        widget = forms.Textarea(attrs={'class':'required span10','rols':0, 'cols':0, 'style':'height:100px;resize:none;'},) )


class pgTypeWidget(forms.MultiWidget):

    def __init__(self, first_widget, second_widget):
        widgets = (first_widget, second_widget)
        super(pgTypeWidget, self).__init__(widgets, None)

    def decompress(self, value):
        if value:
            return value.split('|')
        return [None, None]

    def render(self, name, value, attrs=None):
        '''
        forcing td elements to be part of the rendered output
        ''' 
        _temp = super(pgTypeWidget, self).render(name, value, attrs)
        _l = _temp.split(u'</select><')
        o = u'<td class="contains-input">{first_form}</td><td class="contains-input">{second_form}</td></tr>'
        o = o.format(
            first_form = _l[0] + u'</select>',
            second_form = u'<' + _l[1]
            )
        return SafeUnicode(o)


class pgTypeField(forms.MultiValueField):
    # widget = pgTypeWidget()

    def __init__(self, first_field, *args, **kwargs):

        fields = (
            first_field,
            forms.ChoiceField(
                choices = ( 
                    ("_default", "",), # made the empty string to contain something to bypass
                                      # non-empty validation test
                    ("[]","[]") 
                ),
                widget = forms.Select(attrs={'style':'width:40px;'}),
                required = False, 
                ),
        )

        self.widget = pgTypeWidget(fields[0].widget, fields[1].widget)
        super(pgTypeField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        return "|".join(data_list)


class BaseColumnForm(forms.BaseForm):
    '''
    abstract class to which houses the common code between ColumnForm and TableForm
    '''
    
    def __init__(self, dialect, engines=[], charsets=[], column_form_count=1, 
        existing_tables = [], existing_columns = None, **kwargs):
        f = SortedDict()
        # variable amount of column_form_count
        # field label's are directly tied to the corresponding template
        for i in range( column_form_count ):
            sufx = '_' + str(i)
            f['name'+sufx] = forms.CharField(
                widget=forms.TextInput(attrs={'class':'required'}),
                label = 'name')

            if dialect == 'postgresql':
                type_choice = forms.ChoiceField(
                    choices = fns.make_choices(pgsql_types),
                    widget = forms.Select(attrs={'class':'required'}),
                    initial = 'character varying'
                    )
                
                f['type' + sufx] = pgTypeField(type_choice,
                    label = 'type', required=True,
                    )

            elif dialect == 'mysql':
                f['type'+sufx] = forms.ChoiceField(
                    choices = fns.make_choices(mysql_types),
                    widget = forms.Select(attrs={'class':'required needs:values:set|enum select_requires:values'
                        +sufx+':set|enum select_requires:length'+sufx+':varchar|varbinary'}),
                    initial = 'varchar',
                    label = 'type',
                )
    
            if dialect == 'mysql':
                # this field is only displayed when the type field is set to one of any types
                # that needs this e.g. (enum and set)
                f['values'+sufx] = forms.CharField(
                    label = 'values', required = False, 
                    help_text="Enter in the format: ('yes','false')",
                )

            f['length'+sufx] = forms.IntegerField(
                widget=forms.TextInput(attrs={'class':'validate-integer'}),
                label = 'size', required=False, )
            f['key'+sufx] = forms.ChoiceField(
                required = False,
                widget = forms.Select(attrs={'class':'even'}),
                choices = fns.make_choices(key_choices),
                label = 'key',
            )
            f['default'+sufx] = forms.CharField(
                required = False,
                label = 'default',
                widget=forms.TextInput
            )
            if dialect == 'postgresql':
                f['not_null'+sufx] = forms.BooleanField(
                    required=False, label='not null')

            elif dialect == 'mysql':
                f['charset'+sufx] = forms.ChoiceField(
                    choices = fns.make_choices(charsets), 
                    initial='latin1',
                    label = 'charset',
                    widget=forms.Select(attrs={'class':'required'})
                )

                f['other'+sufx] = forms.MultipleChoiceField(
                    choices = fns.make_choices(mysql_other_choices, True),
                    widget = tt_CheckboxSelectMultiple(attrs={'class':'occupy'}),
                    required = False,
                    label = 'other',
                )

        # complete form creation process
        self.base_fields = f
        forms.BaseForm.__init__(self, **kwargs)


class TableForm(BaseColumnForm):

    def __init__(self, **kwargs):
        BaseColumnForm.__init__(self, dialect, **kwargs)
        # store the previous contents of self.fields and start again: achieves desired ordering of fields
        _temp = self.fields
        self.fields = SortedDict()

        self.fields['name'] = forms.CharField(widget=forms.TextInput(attrs={'class':'required'}))

        if dialect == 'mysql':

            self.fields['charset'] = forms.ChoiceField(
                choices = fns.make_choices(charsets),
                initial='latin1'
            )

            engine_list, default_engine = [], ''
            for tup in engines:
                engine_list.append((tup[0],))
                if tup[1] == 'DEFAULT':
                    default_engine = tup[0]

            self.fields['engine'] = forms.ChoiceField(
                required = False, 
                choices = fns.make_choices( engine_list ),
                initial = default_engine
            )
        self.fields.update(_temp)


class ColumnForm(BaseColumnForm):

    def __init__(self, dialect, existing_columns=[], **kwargs):
        BaseColumnForm.__init__(self, dialect, **kwargs)

        if dialect == 'mysql':
            self.fields['insert_position'] = forms.ChoiceField(
                choices = fns.make_choices(['at the end of the table', 'at the beginning'], True)
                    + fns.make_choices(existing_columns,False,'--------','after'),
                label = 'insert this column',
                initial = 'at the end of the table',
                widget = forms.Select(attrs={'class':'required'}),
            )


class ForeignKeyForm(forms.BaseForm):

    def __init__(self, dialect, default_schema=None, schema_list=[], table_list = [], 
        current_table_columns = [], **kwargs):
        f = SortedDict() # ordered structure
        # name field has a default
        f['name'] = forms.CharField(
                widget = forms.TextInput(attrs={'class':'required'}),
                # initial = 'auto generated',
                help_text = 'leave empty to use an auto generated name',
            )
        f['referred_schema'] = forms.ChoiceField (
                choices = fns.make_choices(schema_list),
                initial = default_schema,
                widget = forms.Select(attrs={'class':'required'}),
            )
        f['referred_table'] = forms.ChoiceField (
            choices = fns.make_choices(table_list),
            widget = forms.Select(attrs={'class':'required'}),
            )
        f['constrained_columns'] = forms.CharField()
        f['referred_columns'] = forms.CharField()

        self.fields = f
        super(ForeignKeyForm, self).__init__(dialect, **kwargs)


def get_dialect_form(form_name, dialect):
    '''
    If there are two very different implementations of a form for the same functions.
    they would be listed in their dialect order as described below in dialect_forms

    Then this function would be used to get the dialect specific information of that form.
    very boring function. I even deleted it once.


    structure of dialect_forms:
        { 'form_name': [ postgresql version of form_name, mysql version of form_name] }
    '''
    dialect_forms = {
        # 'DbForm': [pgsqlDbForm, mysqlDbForm],
        'TableEditForm': [pgTableEditForm, mysqlTableEditForm],
    }
    dialects_order = ['postgresql', 'mysql']

    return dialect_forms[form_name][ dialects_order.index(dialect) ]



