from itertools import chain
from django.utils.encoding import StrAndUnicode, force_unicode
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe
from django.forms import widgets
from django import forms

pgsql_types = ('bigint', 'bigserial', 'bit', 'bit varying', 'boolean', 'bytea', 
    'character varying', 'character', 'cidr', 'date', 'double precision', 'inet', 'integer', 
    'lseg', 'macaddr', 'money', 'numeric', 'real', 'smallint', 'serial', 'text', 'time', 
    'time with time zone', 'timestamp', 'timestamp with time zone', 'uuid', 'xml')

pgsql_encoding = ('UTF8', 'SQL_ASCII', 'BIG5', 'EUC_CN', 'EUC_JP', 'EUC_KR', 'EUC_TW',
    'GB18030', 'GBK', 'ISO_8859_5', 'ISO_8859_6', 'ISO_8859_7', 'ISO_8859_8', 'JOHAB',
    'KOI8R', 'KOI8U', 'LATIN1', 'LATIN2', 'LATIN3', 'LATIN4', 'LATIN5', 'LATIN6', 'LATIN7',
    'LATIN8', 'LATIN9', 'LATIN10', 'MULE_INTERNAL', 'WIN866', 'WIN874', 'WIN1250', 'WIN1251',
    'WIN1252', 'WIN1253', 'WIN1254', 'WIN1255', 'WIN1256', 'WIN1257', 'WIN1258')

mysql_types = ('varchar', 'char', 'text', 'tinytext', 'mediumtext', 'longtext', 'tinyint',
    'smallint', 'mediumint', 'int', 'bigint', 'real', 'double', 'float', 'decimal', 'numeric',
    'date', 'time', 'datetime', 'timestamp', 'tinyblob', 'blob', 'mediumblob', 'longblob', 'binary',
    'varbinary', 'bit', 'enum', 'set')

key_choices = ('primary','unique','index')

mysql_other_choices = ('unsigned','binary','not null','auto increment' )

user_privilege_choices = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP',
    'ALTER', 'INDEX', 'CREATE TEMPORARY TABLES']
admin_privilege_choices = ('FILE','PROCESS','RELOAD', 'SHUTDOWN','SUPER')

pgsql_privileges_choices = ('INHERIT','CREATEDB','CREATEROLE','REPLICATION','SUPERUSER')

format_choices = ( ('SQL', 'sql'),('CSV', 'csv') )

export_choices = ( ('structure', 'structure'),('data', 'data') )

foreign_key_action_choices = ['no action', 'restrict', 'cascade', 'set null', 'set default']


class tt_CheckboxSelectMultiple(widgets.CheckboxSelectMultiple):
    """
    Copy of that found in stock django but added here in other to change its rendering (
    addition of a class to part of its rendered html)
    """

    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = [u'<ul class="inputs-list">']
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_unicode(option_label))
            output.append(u'<li><label%s>%s <span>%s</span></label></li>' % (label_for, rendered_cb, option_label))
        output.append(u'</ul>')
        return mark_safe(u'\n'.join(output))


class tt_RadioFieldRenderer(widgets.RadioFieldRenderer):
    """
    Copy of that found in stock django but added here in other to change its rendering (
    addition of a class to part of its rendered html)
    """

    def render(self):
        """Outputs a <ul> for this set of radio fields."""
        return mark_safe(u'<ul class="inputs-list">\n%s\n</ul>' % u'\n'.join([u'<li>%s</li>'
                % force_unicode(w) for w in self]))

