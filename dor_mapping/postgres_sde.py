def set_current_version(db_conn, child_version): 
    '''
    Set which geodatabase version and state you will access.
    '''
    with db_conn.cursor() as cur:
        cur.execute("SELECT sde.sde_set_current_version(%s)", (child_version,))
        rv = cur.fetchone()[0]
        if rv != 0: 
            raise ValueError(f'Expected return value of 0, instead received: {rv} for sde_set_current_version. Is "{child_version}" correct?')
        print(f'Successfully set {child_version} named version edit session')

def begin_edit_version(db_conn, child_version): 
    '''
    Begin an edit session on a named version
    '''
    _edit_version(db_conn, child_version, 1)

def end_edit_version(db_conn, child_version): 
    '''
    End an edit session on a named version
    '''
    _edit_version(db_conn, child_version, 2)

def _edit_version(db_conn, child_version, param): 
    '''
    Begin or end an edit session on a named version
    '''
    with db_conn.cursor() as cur:
        cur.execute("SELECT sde.sde_edit_version(%s,%s)", (child_version, param))
        rv = cur.fetchone()[0]
        if rv != 0: 
            raise ValueError(f'Expected return value of 0, instead received: {rv} for sde_edit_version. Is "{child_version}" correct?')
        print(f'Successfully {"started" if param == 1 else "ended" if param == 2 else param} "{child_version}" named version edit session')
