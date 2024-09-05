from typing import List
from flask import g, current_app
from . import postgres_code as postgres
from . import utils as util
import psycopg
from psycopg import sql, rows

if current_app.config['TESTING'] == False: 
    DB_CREDS = util.get_aws_secret('E3/dor_mapping/dor')
else: 
    DB_CREDS = util.get_aws_secret('E3_Testing/dor_mapping/dor')

DB_CREDS['user'] = DB_CREDS['username']
DB_CREDS.pop('username')
SCHEMA = 'dor'
TABLE = 'parcel_rev_evw'
LOGGING_TABLE = 'pin_requests'
SEQUENCE = 'pin_request_seq'
PIN_COLUMN = 'pin'
PIN_ASSIGNED_COLUMN = 'pin_assigned'

def get_db(user, password):
    '''
    Verify that the user can access the database with their credentials. A named 
    version edit session can only be opened by logging in as the version owner. 
    '''
    g.db = postgres.connect_to_db(DB_CREDS, **{'user': user, 'password': password})
    return g.db

def get_default_db(named_version):
    '''
    Return the actual database connection that will be used to perform the work 
    and begin an SDE edit session in the user's name. A named version edit session 
    can only be opened by logging in as the version owner. 
    '''
    g.db = postgres.connect_to_db(DB_CREDS)
    postgres.sde.set_current_version(g.db, named_version)
    postgres.sde.begin_edit_version(g.db, named_version)
    return g.db

def initiate(db_conn, form): 
    '''
    Initiate the database sequence: 
    1. Get the objectids that fit the addr_std, mapreg, and have correct status and
    null PIN
    2. Update the named_version for those objectids to be the next values in the 
    sequence. The sequence will increment even if the transaction is rolled back.
    3. Check if the newly created PIN creates a duplicate and raise an error if so
    4. Insert the request into a logging table capturing who made the request, what 
    information they provided, and when they made the request
    5. Use the same objectids to return the newly updated views
    '''
    # named_version edit session must already be opened
    addr_std = form['addr_std']
    mapreg = form['mapreg']
    parcel_type = form['parcel_type'].lower().strip()
   
    # 1. 
    object_ids = select_object_ids(db_conn, addr_std, mapreg)
    if len(object_ids) == 0: 
        return [], []
    # 2.
    update_pin(db_conn, object_ids)
    # 3.
    new_pins = get_new_pins(db_conn, object_ids)
    header, results = check_pin_duplicates(db_conn, new_pins)
    if len(results) != 0: 
        raise AssertionError(f'Newly generated PINs are already in use. Please contact maps@phila.gov and provide the following PINs and PIN active parcel counts:\n{(header, results)}')
    # 4.
    insert_request(db_conn, object_ids, parcel_type)
    # 5. 
    return select_results(db_conn, object_ids)

def select_object_ids(db_conn, addr_std, mapreg) -> List[int]:
    '''
    Return the objectids for parcels with a given addr_std and mapreg, where the PIN 
    is null and the status is in (1,3)
    '''
    with db_conn.cursor(row_factory = rows.dict_row) as cur:
        data = (addr_std, mapreg)
        
        if addr_std == '': 
            addr_std_null = ' OR addr_std IS NULL'
        else: 
            addr_std_null = ''
        if mapreg == '': 
            mapreg_null = ' OR mapreg IS NULL'
        else: 
            mapreg_null = ''

        statement = (sql.SQL('''
            SELECT objectid 
            FROM {table} 
            WHERE status IN (1,3) 
                AND (addr_std = %s{addr_std_null}) 
                AND (mapreg = %s{mapreg_null}) 
                AND {pin} IS NULL''')
            .format(
                table=sql.Identifier(SCHEMA, TABLE), 
                pin=sql.Identifier(PIN_COLUMN), 
                addr_std_null=sql.SQL(addr_std_null), 
                mapreg_null=sql.SQL(mapreg_null)))
        try: 
            cur.execute(statement, data)
            postgres._print_success(db_conn, statement, 'SELECT')
            return postgres.dict_row_to_list(cur.fetchall(), 'objectid')
        except Exception as e: 
            postgres._print_data_error(db_conn, statement, e, exit=False)                

def update_pin(db_conn, object_ids: List[int]): 
    '''
    Update the PINs in the named_version for the given objectids. Note that in 
    psycopg >= 3.0, the following SQL
        WHERE xxxx IN (n,n,n,...)
    Must be written as
        WHERE objectid = ANY(%s)
    '''
    with db_conn.cursor(row_factory = rows.tuple_row) as cur:
        statement = (sql.SQL(
            'UPDATE {} SET {} = nextval(%s) WHERE objectid = ANY(%s)')
            .format(
                sql.Identifier(SCHEMA, TABLE), 
                sql.Identifier(PIN_COLUMN)))
        try: 
            cur.execute(statement, [SEQUENCE, object_ids])
            postgres._print_success(db_conn, statement, 'UPDATE')
        except Exception as e: 
            postgres._print_data_error(db_conn, statement, e, exit=False, data=object_ids)            

def get_new_pins(db_conn, object_ids: List[int]) -> List[int]: 
    '''
    Return the newly created PINs for the objectids that were just updated
    '''
    with db_conn.cursor(row_factory = rows.dict_row) as cur:
        statement = (sql.SQL(
            'SELECT {} FROM {} WHERE status IN (1,3) AND objectid = ANY(%s)')
            .format(
                sql.Identifier(PIN_COLUMN),
                sql.Identifier(SCHEMA, TABLE)))
        try: 
            cur.execute(statement, [object_ids])
            postgres._print_success(db_conn, statement, 'SELECT')
            return postgres.dict_row_to_list(cur.fetchall(), PIN_COLUMN)
        except Exception as e: 
            postgres._print_data_error(db_conn, statement, e, exit=False)  

def check_pin_duplicates(db_conn, pins: List[int]) -> bool: 
    '''
    Check if the newly created PIN(s) create(s) a duplicate, returning any duplicate 
    PINs and their counts
    '''
    with db_conn.cursor(row_factory = rows.tuple_row) as cur:
        statement = (sql.SQL(
'''
select * 
from (
	select {column} , count(*) as count
	from {table}
    where status in (1,3)
	group by {column} 
	having {column} is not null 
	order by {column}
    ) as counts
where {column} = ANY(%s) and counts.count > 1
''')
            .format(
                column=sql.Identifier(PIN_COLUMN), 
                table=sql.Identifier(SCHEMA, TABLE)))           
        try: 
            cur.execute(statement, [pins])
            postgres._print_success(db_conn, statement, 'SELECT')
            return cur.description, cur.fetchall()
        except Exception as e: 
            postgres._print_data_error(db_conn, statement, e, exit=False)  

def insert_request(db_conn, object_ids, parcel_type): 
    '''
    Insert a row for each updated parcel into the logging table with the new PINs
    and the information provided by the user, again utilizing the objectids to specify the rows
    '''
    with db_conn.cursor(row_factory = rows.tuple_row) as cur:
        statement = (sql.SQL(
'''INSERT INTO {} ({}, requester_named_version, addr_std, mapreg, parcel_type, parcel_objectid, request_date)
SELECT {} , {}, addr_std , mapreg , {}, objectid , now() 
FROM {}
WHERE objectid = ANY(%s)''')
            .format(
                sql.Identifier(SCHEMA, LOGGING_TABLE), 
                sql.Identifier(PIN_ASSIGNED_COLUMN), 
                sql.Identifier(PIN_COLUMN), 
                sql.Literal(g.named_version), 
                sql.Literal(parcel_type), 
                sql.Identifier(SCHEMA, TABLE)))
        try: 
            cur.execute(statement, [object_ids])
            postgres._print_success(db_conn, statement, 'INSERT')
        except Exception as e: 
            postgres._print_data_error(db_conn, statement, e, exit=False, data=object_ids)        

def select_results(db_conn, object_ids): 
    '''
    Return the information for the parcels given new PINs. Duplicate the PIN column 
    so that it also appears as the first column in the returned results. 
    '''
    with db_conn.cursor(row_factory = rows.tuple_row) as cur:
        statement = (sql.SQL(
            'SELECT {} as "NEW PIN" , * FROM {} WHERE objectid = ANY(%s)')
            .format(
                sql.Identifier(PIN_COLUMN), 
                sql.Identifier(SCHEMA, TABLE)))
        try: 
            cur.execute(statement, [object_ids])
            postgres._print_success(db_conn, statement, 'SELECT')
            return cur.description, cur.fetchall()
        except Exception as e: 
            postgres._print_data_error(db_conn, statement, e, exit=False, data=object_ids)                

def get_duplicate_pins(db_conn) -> List: 
    '''
    Get a list of duplicate PINs and their counts on active parcels
    '''
    with db_conn.cursor(row_factory = rows.tuple_row) as cur:
        statement = (sql.SQL('''
            SELECT foo.{pin} AS "PIN", foo.count AS "Duplicates Count"
            FROM (
                SELECT parcel.{pin}, COUNT(*) AS count
                FROM {table} parcel
                WHERE parcel.status = ANY(ARRAY[1,3])
                GROUP BY parcel.{pin}) foo
            WHERE foo.count > 1 and foo.{pin} is not null
            ORDER BY foo.count DESC , foo.{pin}''')
            .format(
                pin=sql.Identifier(PIN_COLUMN), 
                table=sql.Identifier(SCHEMA, TABLE)))
        try: 
            cur.execute(statement)
            postgres._print_success(db_conn, statement, 'SELECT')
            return cur.description, cur.fetchall()
        except Exception as e: 
            postgres._print_data_error(db_conn, statement, e, exit=False)   

def get_missing_pins(db_conn) -> List: 
    '''
    Get a list and count of active parcels missing pins
    '''
    with db_conn.cursor(row_factory = rows.tuple_row) as cur:
        statement = (sql.SQL('''
            SELECT 
                CASE 
		            WHEN pre.addr_std IS NULL THEN ''
	                ELSE pre.addr_std
                END AS addr_std , 
                CASE 
                    WHEN pre.mapreg IS NULL THEN ''
                    ELSE pre.mapreg 
	            END AS mapreg , 
                COUNT(*) AS "Count Missing PINs"
            FROM {table} AS pre
            WHERE pre.status = ANY(ARRAY[1,3]) and pre.{pin} IS NULL
            GROUP BY pre.addr_std , pre.mapreg 
            ORDER BY COUNT(*) DESC , pre.addr_std , pre.mapreg
            ''')
            .format(
                table=sql.Identifier(SCHEMA, TABLE),
                pin=sql.Identifier(PIN_COLUMN)))
        try: 
            cur.execute(statement)
            postgres._print_success(db_conn, statement, 'SELECT')
            return cur.description, cur.fetchall()
        except Exception as e: 
            postgres._print_data_error(db_conn, statement, e, exit=False)   

def close_db(e=None):
    '''
    Close database connection and end edit session if it exists
    '''
    db = g.pop('db', None)
    named_version = g.pop('named_version', None)
    if db is not None:
        if named_version is not None: 
            try: 
                postgres.sde.end_edit_version(db, named_version)
                print(f'    Successfully closed "{named_version}" named version edit session')
            except (psycopg.errors.RaiseException, ValueError) as e: 
                pass
        db.close()

def init_app(app):
    '''
    Registers a function to be called when the application context is popped.
    '''
    app.teardown_appcontext(close_db)
