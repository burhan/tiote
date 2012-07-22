from tiote import sa
from sqlalchemy import text


def stored_query(query_type):
    
    queries_db = {

    'variables':
        "SHOW server_version",
    
    'template_list':
        "SELECT datname FROM pg_catalog.pg_database",
    
    'group_list':
        "SELECT rolname FROM pg_catalog.pg_roles WHERE rolcanlogin=False",
    
    'db_list':
        "SELECT datname FROM pg_catalog.pg_database WHERE datistemplate = 'f' ORDER BY datname ASC;",
    
    'user_rpr':
        "SELECT rolname, rolcanlogin, rolsuper, rolinherit, rolvaliduntil FROM pg_catalog.pg_roles",
    
    'user_list':
        "SELECT rolname FROM pg_catalog.pg_roles",
    
    'table_list':
        "SELECT schemaname, tablename FROM pg_catalog.pg_tables ORDER BY schemaname DESC",
    
    'full_schema_list':
        """
        SELECT 
            schema_name, schema_owner 
        FROM 
            information_schema.schemata
        WHERE 
            schema_name NOT LIKE '%pg_toast%' AND 
            schema_name NOT LIKE '%pg_temp%'
        """,
    
    'user_schema_list':
        """
        SELECT 
            schema_name, schema_owner 
        FROM 
            information_schema.schemata
        WHERE 
            schema_name NOT LIKE '%pg_toast%' AND
            schema_name NOT LIKE '%pg_temp%' AND
            schema_name NOT IN ('pg_catalog', 'information_schema'),
        """,
        # - system catalogs are discovered
    
    'db_rpr':
        """
        SELECT 
            datname as name, 
            pg_encoding_to_char(encoding) as encoding,
            datcollate AS "collation",
            datctype AS "character type"
        FROM 
            pg_catalog.pg_database 
        WHERE
            datname not like \'%template%\' 
        """,
    
    }
    
    return queries_db[query_type]


def generate_query(query_type, query_data=None):
    bindparams = sa.transform_args_to_bindparams(query_data)

    if query_type == 'create_user':
        # create role statement
        q0 = "CREATE ROLE {role_name}".format(**query_data)
        if query_data['can_login']:
            q0 += " LOGIN"
        if query_data['password']:
            q0 += " ENCRYPTED PASSWORD '{password}'".format(**query_data)
        if query_data['role_privileges']:
            for option in query_data['role_privileges']:
                q0 += " " + option
        if query_data['connection_limit']:
            q0 += " CONNECTION LIMIT {connection_limit}".format(**query_data)
        if query_data['valid_until']:
            q0 += " VALID UNTIL '{valid_until}'".format(**query_data)
        if query_data['group_membership']:
            q0 += " IN ROLE"
            for grp_index in range( len(query_data['group_membership']) ):
                if grp_index == len(query_data['group_membership']) - 1:
                    q0 += " " + query_data['group_membership'][grp_index]
                else:
                    q0 += " " + query_data['group_membership'][grp_index] + ","
#            if query_data['comment']:
#                q1 = "COMMENT ON ROLE {role_name} IS \'{comment}\'".format(**query_data)
#                queries.append(q1)
        queries = (q0, )
        return queries
    
    elif query_type == 'drop_user':
        queries = []
        for cond in query_data:
            q = "DROP ROLE {rolname}".format(**cond)
            queries.append(q) 
        return tuple(queries)
    
    elif query_type == 'create_db':
        _l = []
        _l.append("CREATE DATABASE {name}")
        if query_data['encoding']: _l.append(" WITH ENCODING='{encoding}'")
        if query_data['owner']: _l.append(" OWNER={owner}")
        if query_data['template']: _l.append(" TEMPLATE={template}")
        return ("".join(_l).format(**query_data), )
    
    elif query_type == 'table_rpr':
        stmt = """
        SELECT 
            t2.tablename AS table,
            t2.tableowner AS owner, 
            t2.tablespace, 
            t1.reltuples::integer AS "estimated row count"
        FROM 
            pg_catalog.pg_class as t1 
            INNER JOIN pg_catalog.pg_tables AS t2
            ON t1.relname = t2.tablename
        WHERE 
            t2.schemaname= :schm 
        ORDER BY t2.tablename ASC
        """
        q0 = text(stmt, bindparams=bindparams)
        return (q0, )
    
    elif query_type == 'constraints':
        stmt = """
        SELECT 
            con.contype, -- f, c, p, u 
            con.conname,  --sometimes annoyingly long
            con.conkey, -- constrained columns
            con.confkey, -- referred columns of a foreign key
            cl.relname, -- the table the fkey refers to
            con.consrc -- definition of a check constraint
        
        FROM 
            pg_constraint AS con
            LEFT OUTER JOIN pg_class AS cl ON cl.oid = con.confrelid
            
        WHERE
            con.connamespace = (
                SELECT oid 
                FROM pg_namespace 
                WHERE nspname = :schm
            )  AND
            
            con.conrelid = (
                SELECT oid 
                FROM pg_class 
                WHERE relname = :tbl
            )
        """
        q0 = text(stmt, bindparams=bindparams)
        return (q0,)
    
    elif query_type == 'primary_keys':
        stmt = """
        SELECT 
            kcu.column_name, kcu.constraint_name, tc.constraint_type
        FROM 
            information_schema.key_column_usage AS kcu
            LEFT OUTER JOIN information_schema.table_constraints AS tc
            ON (kcu.constraint_name = tc.constraint_name) 
        WHERE
            kcu.table_name = :tbl AND 
            kcu.table_schema = :schm AND 
            kcu.table_catalog = :db AND 
            (tc.constraint_type='PRIMARY KEY')
        """
        q0 = text(stmt, bindparams=bindparams)
        return (q0, )
    
    elif query_type == 'table_structure':
        stmt = """
        SELECT 
            column_name as column,
            data_type as type,
            is_nullable as nullable,
            column_default as default, 
            character_maximum_length, 
            numeric_precision, numeric_scale, datetime_precision,
            interval_type, interval_precision 
        FROM 
            information_schema.columns
        WHERE 
            table_catalog = :db AND 
            table_schema = :schm AND 
            table_name = :tbl
        ORDER BY ordinal_position ASC
        """
        q0 = text(stmt, bindparams=bindparams)
        return (q0, )

    elif query_type == 'column_assoc':
        stmt = """
        SELECT
            ordinal_position AS pos,
            column_name AS column

        FROM
            information_schema.columns

        WHERE 
            table_catalog = :db AND 
            table_schema = :schm AND 
            table_name = :tbl
        """
        q0 = text(stmt, bindparams=bindparams)
        return (q0, )

    elif query_type == 'foreign_key_relation':
        stmt = """
        SELECT 
            conname, 
            confrelid::regclass AS "referenced_table",
            conkey AS array_local_columns, 
            confkey AS array_foreign_columns
        FROM 
            pg_constraint 
        WHERE 
            contype = 'f' 
            AND conrelid::regclass =  :tbl::regclass
            AND connamespace = (
                SELECT oid 
                FROM pg_namespace 
                WHERE nspname= :schm) 
        """
        q0 = text(stmt, bindparams=bindparams)
        return (q0, )
    
    elif query_type == 'seqs_rpr':
    # very ugly query and sometimes take long to run.
    # it increments every sequence and decrements to get the current value
    # reasons why its this long:
    # netval gives the minimum_value for a new sequence(have never been consumed).
    # on reseting the value of the sequence to its previous the case above results in an error
    # so this long query circumvents that error by adding a CASE construct
        stmt = """
        WITH temp_seqs_tbl AS (
            SELECT
                sequence_name,
                start_value, minimum_value, increment, maximum_value, 
                nextval(sequence_name::text)
            FROM 
                information_schema.sequences
            WHERE 
                sequence_schema = :schm
        )
        SELECT 
            sequence_name AS name, 
            start_value, minimum_value, increment, maximum_value, 
            CASE 
                WHEN nextval::bigint=start_value::bigint THEN
                    setval(sequence_name::text, start_value::bigint, false)
                WHEN nextval::bigint<>start_value::bigint THEN
                    setval(sequence_name::text, lastval() - 1, true)
            END
        FROM
            temp_seqs_tbl
        """
        q0 = text(stmt, bindparams=bindparams)
        return (q0, )

    elif query_type == 'drop_sequence':
        queries = []
        for where in query_data['conditions']:
            where['name'] = where['name'].replace("'", "")
            queries.append( "DROP SEQUENCE {schm}.{name}".format(schm=query_data['schm'], **where))
        return tuple(queries)

    elif query_type == 'reset_sequence':
        queries = []
        for where in query_data['conditions']:
            where['name'] = where['name'].replace("'", "")
            queries.append( "ALTER SEQUENCE {schm}.{name} RESTART".format(
                schm=query_data['schm'], **where )
            )
        return tuple(queries)

    elif query_type == 'pgadmin_deps':
        # lifted from pgadmin3
        stmt = '''
        SELECT DISTINCT 
            dep.deptype, dep.classid, cl.relkind, ad.adbin, ad.adsrc, 
            CASE WHEN cl.relkind IS NOT NULL THEN cl.relkind || COALESCE(dep.objsubid::text, '')
                WHEN tg.oid IS NOT NULL THEN 'T'::text
                WHEN ty.oid IS NOT NULL THEN 'y'::text
                WHEN ns.oid IS NOT NULL THEN 'n'::text
                WHEN pr.oid IS NOT NULL THEN 'p'::text
                WHEN la.oid IS NOT NULL THEN 'l'::text
                WHEN rw.oid IS NOT NULL THEN 'R'::text
                WHEN co.oid IS NOT NULL THEN 'C'::text || contype
                WHEN ad.oid IS NOT NULL THEN 'A'::text
                ELSE '' END AS type,
            COALESCE(coc.relname, clrw.relname) AS ownertable,
            CASE WHEN cl.relname IS NOT NULL AND att.attname IS NOT NULL THEN cl.relname || '.' || att.attname
                ELSE COALESCE(cl.relname, co.conname, pr.proname, tg.tgname, ty.typname, la.lanname, rw.rulename, ns.nspname)
            END AS refname,
            COALESCE(nsc.nspname, nso.nspname, nsp.nspname, nst.nspname, nsrw.nspname) AS nspname

        FROM
            pg_depend dep
            LEFT JOIN pg_class cl ON dep.objid=cl.oid
            LEFT JOIN pg_attribute att ON dep.objid=att.attrelid AND dep.objsubid=att.attnum
            LEFT JOIN pg_namespace nsc ON cl.relnamespace=nsc.oid
            LEFT JOIN pg_proc pr ON dep.objid=pr.oid
            LEFT JOIN pg_namespace nsp ON pr.pronamespace=nsp.oid
            LEFT JOIN pg_trigger tg ON dep.objid=tg.oid
            LEFT JOIN pg_type ty ON dep.objid=ty.oid
            LEFT JOIN pg_namespace nst ON ty.typnamespace=nst.oid
            LEFT JOIN pg_constraint co ON dep.objid=co.oid
            LEFT JOIN pg_class coc ON co.conrelid=coc.oid
            LEFT JOIN pg_namespace nso ON co.connamespace=nso.oid
            LEFT JOIN pg_rewrite rw ON dep.objid=rw.oid
            LEFT JOIN pg_class clrw ON clrw.oid=rw.ev_class
            LEFT JOIN pg_namespace nsrw ON clrw.relnamespace=nsrw.oid
            LEFT JOIN pg_language la ON dep.objid=la.oid
            LEFT JOIN pg_namespace ns ON dep.objid=ns.oid
            LEFT JOIN pg_attrdef ad ON ad.oid=dep.objid

        WHERE 
            dep.refobjid::regclass = '{schm}.{tbl}'::regclass AND
            classid  IN (
                SELECT oid 
                FROM pg_class
                WHERE relname IN ('pg_class', 'pg_constraint', 'pg_conversion', 'pg_language', 'pg_proc',
                              'pg_rewrite', 'pg_namespace', 'pg_trigger', 'pg_type', 'pg_attrdef')
            )

        ORDER BY  classid, cl.relkind;

        '''
        q0 = stmt.format(**query_data)
        return (q0, )

    elif query_type in ('reindex_table', 'analyze_table'):
        sql_stmt = '{command} {obj}'
        sql_stmt = sql_stmt.format(
            command = 'REINDEX TABLE' if query_type == 'reindex_table' else 'ANALYZE',
            obj = query_data.get('tbl')
        )
        return (sql_stmt, )


def col_defn(col_data, i):
    '''
    returns individual column creation statement; excluding indexes and keys

    used with iterations, i = str(i) where i is index of current iterations
    '''
    # map some keys to meaningful variable names
    type_field = col_data['type_'+i]
    length_field = col_data['length_'+i]
    name_field = col_data['name_'+i]
    key_field = col_data['key_'+i]

    sql_stmt = ' {name} {type}'.format(name=name_field, type=type_field)
    # types with length
    # for type 'interval' length actually denotes 'precision'
    if type_field in ('bit', 'bit varying', 'character varying', 'character', 'interval'):
        sql_stmt += '({length_'+i+'})'
    # date types really have a somewhat different syntax when it has length(actually its precision field).
    # rewrite the contents of sql_stmt to this syntax
    if length_field and ( type_field.startswith('time') or type_field.startswith('timestamp')):
        _in = 9 if type_field.startswith('timestamp') else 4 # the length of time and timestamp respectively
        # restart column definition statement
        sql_stmt = ' {name} {type_prefix} ({length}) {type_postfix}'.format(
            type_prefix= type_field[0: _in],
            length = length_field,
            type_postfix = type_field[_in+1: ] # +1 to avoid the whitespace
            )
    # nullable
    sql_stmt += ' NOT NULL' if col_data['not_null_'+i] else ''
    # handle key
    d = {'primary':'PRIMARY KEY', 'unique':'UNIQUE', 'index':"INDEX"}
    if key_field:
        sql_stmt += ' '+ d[key_field] if key_field != 'unique' else ''
    # done
    return sql_stmt

