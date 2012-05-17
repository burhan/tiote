
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
        "SELECT schema_name, schema_owner FROM information_schema.schemata \
WHERE schema_name NOT LIKE '%pg_toast%' AND schema_name NOT LIKE '%pg_temp%'",
    
    'user_schema_list':
        "SELECT schema_name, schema_owner FROM information_schema.schemata \
WHERE schema_name NOT LIKE '%pg_toast%' AND schema_name NOT LIKE '%pg_temp%' \
AND schema_name NOT IN ('pg_catalog', 'information_schema')" # manually filled, might need to be adjusted if new
                                                     # - system catalogs are discovered
    
    }
    
    return queries_db[query_type]


def generate_query(query_type, query_data=None):
    
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
        q = "SELECT t2.tablename AS table, t2.tableowner AS owner, t2.tablespace, t1.reltuples::integer AS \"estimated row count\" \
FROM ( pg_catalog.pg_class as t1 INNER JOIN pg_catalog.pg_tables AS t2  ON t1.relname = t2.tablename) \
WHERE t2.schemaname='{schm}' ORDER BY t2.tablename ASC".format(**query_data)
        return (q, )
    
    elif query_type == 'indexes':
        q0 = "SELECT kcu.column_name, kcu.constraint_name, tc.constraint_type \
FROM information_schema.key_column_usage AS kcu LEFT OUTER JOIN information_schema.table_constraints \
AS tc on (kcu.constraint_name = tc.constraint_name) WHERE kcu.table_name='{tbl}' \
AND kcu.table_schema='{schm}' AND kcu.table_catalog='{db}'".format(**query_data)
        return (q0,)
    
    elif query_type == 'primary_keys':
        q0 = "SELECT kcu.column_name, kcu.constraint_name, tc.constraint_type \
FROM information_schema.key_column_usage AS kcu LEFT OUTER JOIN information_schema.table_constraints \
AS tc on (kcu.constraint_name = tc.constraint_name) WHERE kcu.table_name='{tbl}' \
AND kcu.table_schema='{schm}' AND kcu.table_catalog='{db}' AND \
(tc.constraint_type='PRIMARY KEY')".format(**query_data)
        return (q0, )
    
    elif query_type == 'table_structure':
        q0 = "SELECT column_name as column, data_type as type, is_nullable as null, \
column_default as default, character_maximum_length, numeric_precision, numeric_scale, \
datetime_precision, interval_type, interval_precision FROM information_schema.columns \
WHERE table_catalog='{db}' AND table_schema='{schm}' AND table_name='{tbl}' \
ORDER BY ordinal_position ASC".format(**query_data)
        return (q0, )
    
    elif query_type == 'table_sequences':
        q0 = 'SELECT sequence_name, nextval(sequence_name::regclass), \
setval(sequence_name::regclass, lastval() - 1, true) FROM information_schema.sequences'
        return (q0, )
    
    elif query_type == 'existing_tables':
        # selects both tables and views
#            q0 = "SELECT table_name FROM information_schema.tables WHERE table_schema='{schm}' \
#ORDER BY table_name ASC".format(**query_data)
        # selects only tables
        q0 = "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='{schm}' \
ORDER BY tablename ASC".format(**query_data)
        return (q0, )

    elif query_type == 'foreign_key_relation':
        q0 = 'SELECT conname, confrelid::regclass AS "referenced_table", \
conkey AS array_local_columns, confkey AS array_foreign_columns \
FROM pg_constraint WHERE contype = \'f\' AND conrelid::regclass = \'{tbl}\'::regclass \
AND connamespace = (SELECT oid from pg_namespace WHERE nspname=\'{schm}\') \
'.format(**query_data)
        return (q0, )
    
    elif query_type == 'db_rpr':
        q0 = 'SELECT datname as name, pg_encoding_to_char(encoding) as encoding, \
datcollate, datctype \
FROM pg_catalog.pg_database \
WHERE name not like \'%template%\' '
        return (q0, )
    
    
    