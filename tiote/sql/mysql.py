
def stored_query(query_type):
    
    queries_db = {
    
    'describe_databases': 
        "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_ROWS FROM `information_schema`.`tables`",
    
    'db_list':
        "SHOW databases",
    
    'user_rpr':
        "SELECT user.`Host`, user.`User` FROM user",
    
    'user_list':
        "SELECT user.`User` FROM user",
    
    'supported_engines':
        "SELECT engine, support FROM `information_schema`.`engines` \
        WHERE support='yes' OR support='default'",
    
    'charset_list':
        "SELECT CHARACTER_SET_NAME FROM INFORMATION_SCHEMA.CHARACTER_SETS",
    
    'variables':
        '''SHOW SESSION VARIABLES WHERE `Variable_name`='version_compile_machine'
        OR `Variable_name`='version_compile_os' OR `variable_name`='version'
        ''',

    'db_rpr':
        'SELECT schema_name as name, default_character_set_name, default_collation_name \
FROM information_schema.schemata',

    }
    
    return queries_db[query_type]


def generate_query(query_type, query_data=None):
    
    if query_type == 'create_user':
        # create user statement
        queries = []
        q1 = "CREATE USER '{username}'@'{host}'".format(**query_data)
        if query_data['password']:
            q1 += " IDENTIFIED BY '{password}'".format(**query_data)
        
        queries.append(q1)
        # grant privileges
        q2 = "GRANT"
        if query_data['privileges'] == 'all':
            q2 += " ALL"
        elif query_data['privileges'] == 'select':
            priv_groups = ['user_privileges','administrator_privileges']
            for priv_group in priv_groups:
                for priv_in in range( len(query_data[priv_group])):
                    if priv_in == len(query_data[priv_group]) - 1:
                        q2 += ' ' + query_data[priv_group][priv_in]
                    else:
                        q2 += ' ' + query_data[priv_group][priv_in] + ','
                        
        if query_data['select_databases'] and len(query_data['select_databases']) > 1:
            for db in query_data['select_databases']: #mutliple grant objects
                q3 = q2 + ' ON {db}.*'.format(database = db)
                # user specification
                q3 += " TO '{username}'@'{host}'".format(**query_data)
                # grant option
                if query_data['options']:
                    q3 += " WITH {options[0]}".format(**query_data)
                # append generated query to queries
                queries.append(q3)
        else:
            # database access
            if query_data['access'] == 'all':
                q4 = q2 + ' ON *.*'
            elif query_data['access'] == 'select':
                q4 = q2 + ' ON {select_databases[0]}.*'.format(**query_data)
                
            # user specification
            q4 += " TO '{username}'@'{host}'".format(**query_data)
            # grant option
            if query_data['options']:
                q4 += " WITH {options[0]}".format(**query_data)
            queries.append(q4)
        return tuple( queries )
    
    elif query_type == 'create_db':
        q = "CREATE DATABASE {name}".format(**query_data)
        if query_data['charset']:
            q += " CHARACTER SET {charset}".format(**query_data)
        return (q, )
    
    elif query_type == 'column_list':
        return ("SELECT column_name FROM information_schema.columns WHERE table_schema='{db}' AND table_name='{tbl}'")
    
    elif query_type == 'drop_user':
        queries = []
        for where in query_data:
            q = "DROP USER '{user}'@'{host}'".format(**where)
            queries.append(q)
        return tuple(queries)
    
    elif query_type == 'table_rpr':
        q = "SELECT TABLE_NAME AS 'table', TABLE_ROWS AS 'rows', TABLE_TYPE AS 'type', ENGINE as 'engine' \
        FROM `INFORMATION_SCHEMA`.`TABLES` WHERE TABLE_SCHEMA = '{db}'".format(**query_data)
        return (q,)
    
    elif query_type == 'indexes':
        q0 = "SELECT DISTINCT kcu.column_name, kcu.constraint_name, tc.constraint_type \
from information_schema.key_column_usage as kcu, information_schema.table_constraints as tc WHERE \
kcu.constraint_name = tc.constraint_name AND kcu.table_schema='{db}' AND tc.table_schema='{db}' \
AND kcu.table_name='{tbl}'".format(**query_data)
        return (q0, )
    
    elif query_type == 'primary_keys':
        q0 = "SELECT DISTINCT kcu.column_name, kcu.constraint_name, tc.constraint_type \
from information_schema.key_column_usage as kcu, information_schema.table_constraints as tc WHERE \
kcu.constraint_name = tc.constraint_name AND kcu.table_schema='{db}' AND tc.table_schema='{db}' \
AND kcu.table_name='{tbl}' AND tc.table_name='{tbl}' \
AND (tc.constraint_type='PRIMARY KEY')".format(**query_data)
        return (q0, )
    
    elif query_type == 'table_structure':
        q0 = 'SELECT column_name AS "column", column_type AS "type", is_nullable AS "null", \
column_default AS "default", extra \
FROM information_schema.columns WHERE table_schema="{db}" AND table_name="{tbl}" \
ORDER BY ordinal_position ASC'.format(**query_data)
        return (q0, )

    elif query_type == 'raw_table_structure':
        q0 = 'SELECT column_name AS "column", data_type AS "type", is_nullable AS "null", \
column_default AS "default", character_maximum_length, numeric_precision, numeric_scale, extra, column_type \
FROM information_schema.columns WHERE table_schema="{db}" AND table_name="{tbl}" \
ORDER BY ordinal_position ASC'.format(**query_data)
        return (q0, )
    
    elif query_type == 'existing_tables':
        q0 = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='{db}'".format(**query_data)
        return (q0, )


