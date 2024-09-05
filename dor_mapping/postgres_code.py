# Required "sudo amazon-linux-extras install postgresql11" on the new server
# Run "python -m IPython" to launch ipython
from typing import List, Dict
import sys
import psycopg 
from psycopg import sql, rows
from . import postgres_sde as sde

def connect_to_db(db_creds: Dict, **kwargs): 
    '''
    Return a Postgresql Connection using a dictionary of credentials. kwargs of 
    the form **{'key' = 'value'} can be used to overwrite the key/value in db_creds.
    '''
    valid = {"host", "port", "dbname", "user", "password"}
    l = []
    for key, value in db_creds.items(): 
        if key in valid: 
            l.append(key + '=' + value)
    conn_string = ' '.join(l)
    try: 
        db_conn = psycopg.connect(conn_string, **kwargs) # row_factory=rows.dict_row
        print(f'''Created new db connection (
    host = {db_conn.info.host}
    dbname = {db_conn.info.dbname}
    user = {db_conn.info.user}
)''')
        return db_conn
    except: 
        print(f'Connection Failed.') # Connection string: {conn_string}') - Warning Reveals User Password

def commit_transactions(db_conn, commit: bool): 
    '''
    Commit all transactions if commit = True, rollback otherwise
    '''
    if commit: 
        db_conn.commit()
    else: 
        db_conn.rollback()
    print(f'All database transactions were {"COMMITTED" if commit else "ROLLED BACK"}')

def select(db_conn, schema: str, table: str, limit:int=None): 
    '''
    SELECT * FROM SCHEMA.TABLE LIMIT N
    '''
    with db_conn.cursor() as cur:
        try: 
            limit_statement = f' LIMIT {limit}' if limit else ''
            statement = sql.SQL("SELECT * FROM {}" + limit_statement).format(sql.Identifier(schema, table))
            print(f'{statement.as_string(db_conn)}')
            cur.execute(statement)
            return cur.fetchall()
        except Exception as e: 
            _print_data_error(db_conn, statement, e)
    _print_success(db_conn, statement, 'SELECT')

def dict_row_to_list(data: List[Dict], field: str) -> List: 
    '''
    Return a list of the values in a column from a postgres SQL table. In other words, 
    given a list of dictionaries (dict_row), return a list of the values belonging 
    to the key "field".
    '''
    l = []
    for record in data: 
        l.append(record[field])
    return l

def _print_success(db_conn, statement: str, type: str): 
    '''
    Internal function to indicate successful step completion. <type> is intended to be 
    one of "SELECT", "UPDATE", "DELETE", etc.
    '''
    print(f'Successfully completed {type} statement:')
    print(f'    {statement.as_string(db_conn)}\n')

def _print_data_error(db_conn, statement: str, e, exit=True, data=None): 
    '''
    Internal function to print the execution statement, data head, data tail, and 
    exception raised by a query, and roll back transaction. 
    '''
    print('Execution Statement Failed:')
    print(f'    {statement.as_string(db_conn)}\n')
    if data != None: 
        print('data[0:5]:')
        for row in data[0:5]: 
            print(f'    {row}')
        print('data[-5:]:')
        for row in data[-5:]: 
            print(f'    {row}')
    print(e)
    commit_transactions(db_conn, False)
    if exit: 
        sys.exit(1)
