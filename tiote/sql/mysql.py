from tiote import sa
from sqlalchemy import text


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
        '''
        SHOW SESSION VARIABLES 
        WHERE 
            `Variable_name`='version_compile_machine' OR 
            `Variable_name`='version_compile_os' OR 
            `variable_name`='version'
        ''',

    'db_rpr':
        """
        SELECT 
            schema_name as name,
            default_character_set_name AS 'character set',
            default_collation_name AS 'collation'
        FROM 
            information_schema.schemata
        """,

    }
    
    return queries_db[query_type]


def generate_query(query_type, query_data=None):
    bindparams = sa.transform_args_to_bindparams(query_data)
    
    # would be a function when users view is reenabled
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
        return ("SELECT column_name FROM information_schema.columns WHERE table_schema= :db AND table_name= :tbl")
    
    elif query_type == 'drop_user':
        queries = []
        for where in query_data:
            q = "DROP USER '{user}'@'{host}'".format(**where)
            queries.append(q)
        return tuple(queries)
    
    elif query_type == 'table_rpr':
        stmt = """
        SELECT 
            TABLE_NAME AS 'table',
            TABLE_ROWS AS 'rows',
            TABLE_TYPE AS 'type',
            ENGINE as 'engine'
        FROM
            information_schema.tables
        WHERE 
            TABLE_SCHEMA = :db
        """
        q0 = text(stmt, bindparams=bindparams)
        return (q0,)
    
    elif query_type == 'indexes':
        stmt = """
        SELECT DISTINCT 
            kcu.column_name AS columns, 
            kcu.constraint_name AS name, 
            tc.constraint_type AS type
        FROM 
            information_schema.key_column_usage as kcu,
            information_schema.table_constraints as tc 
        WHERE 
            kcu.constraint_name = tc.constraint_name 
            AND kcu.table_schema= :db 
            AND tc.table_schema= :db 
            AND kcu.table_name=  :tbl
        """
        q0 = text(stmt, bindparams=bindparams)
        return (q0, )
    
    elif query_type == 'primary_keys':
        stmt = """
        SELECT DISTINCT 
            kcu.column_name, 
            kcu.constraint_name, 
            tc.constraint_type 
        FROM
            information_schema.key_column_usage as kcu,
            information_schema.table_constraints as tc
        WHERE
            kcu.constraint_name = tc.constraint_name AND 
            kcu.table_schema= :db AND 
            tc.table_schema= :db AND
            kcu.table_name= :tbl AND 
            tc.table_name= :tbl AND
            tc.constraint_type='PRIMARY KEY'
        """
        q0 = text(stmt, bindparams=bindparams)
        return (q0, )
    
    elif query_type == 'table_structure':
        stmt ="""
        SELECT 
            column_name AS "column", 
            column_type AS "type", 
            is_nullable AS "nullable",
            column_default AS "default",
            extra 
        FROM
            information_schema.columns 
        WHERE 
            table_schema= :db AND
            table_name= :tbl
        ORDER BY ordinal_position ASC
        """
        q0 = text(stmt, bindparams=bindparams)
        return (q0, )

    elif query_type == 'raw_table_structure':
        stmt = """
        SELECT 
            column_name AS "column", 
            data_type AS "type", 
            is_nullable AS "nullable", 
            column_default AS "default", 
            character_maximum_length, 
            numeric_precision, numeric_scale, extra, column_type
        FROM 
            information_schema.columns 
        WHERE 
            table_schema= :db 
            AND table_name= :tbl
        ORDER BY ordinal_position ASC
        """
        q0 = text(stmt, bindparams=bindparams)
        return (q0, )


def col_defn(col_data, i):
    '''
    returns individual column creation statement; excluding indexes and keys

    used with iterations, i = str(i) where i is index of current iterations
    '''
    
    sql_stmt = ' {name_'+i+'} {type_'+i+'}'
    type_field = col_data['type_'+i]
    # types with length
    if type_field in ['bit','tinyint','smallint','mediumint','int','integer','bigint',
                      # 'real','double','float', # these types needs an extra 'decimals' option
                                                 # before its syntax can have length
                      'decimal','numeric','char','varchar',
                      'binary','varbinary']:
        sql_stmt += '({length_'+i+'})' if col_data['length_'+i] else ''
    # types with unsigned
    if type_field in ['tinyint','smallint','mediumint','int','integer','bigint',
                      'real','double','float','decimal','numeric']:
        sql_stmt += ' UNSIGNED' if 'unsigned' in col_data['other_'+i] else ''
    # types needing values
    if type_field in ['set','enum']:
        sql_stmt += ' {values_'+i+'}' if col_data['values_'+i] else ''
    # types with binary
    if type_field in ['tinytext','text','mediumtext','longtext']:
        sql_stmt += ' BINARY' if 'binary' in col_data['other_'+i] else ''
    # types needing charsets
    if type_field in ['char','varchar','tinytext','text',
                            'mediumtext','longtext','enum','set']:
        sql_stmt += ' CHARACTER SET {charset_'+i+'}'

    sql_stmt += ' AUTO_INCREMENT' if 'auto increment' in col_data['other_'+i] else ''
    # not null
    sql_stmt += ' NOT NULL' if 'not null' in col_data['other_'+i] else ' NULL'
    
    # handle key
    d = {'primary':'PRIMARY KEY', 'unique':'UNIQUE', 'index':"INDEX"}
    key_field = col_data['key_'+i]
    if key_field:
        sql_stmt += ' ' + d[key_field]

    return sql_stmt
