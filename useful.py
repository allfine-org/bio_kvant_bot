import sqlite3
import logging

def use_database(filename : str, request : str, param : tuple | None = (), fetchone : bool = True):
    """Execute a database query.
    
    Return result what the database returned. 
    :type result: tuple | None
    
    :param filename: The name of the .db file where the database will be located
    :type filename: str
    
    :param request: The request that will be executed by the database
    :type request: str
    
    :param param: The parameters to request
    :type param: tuple (default None)

    :param fetchone: If True method returns only one result, else returns as many as find
    :type fetchone: bool (default True)

    Example of usage:
    use_database('database.db', 'UPDATE users SET id = ?', (3,))"""
    fetchone = True
    try:
        # Connecting to database
        conn = sqlite3.connect(filename)
        cursor = conn.cursor()

        # Executing request
        cursor.execute(request, param)

        # Getting result
        if fetchone: result = cursor.fetchone()
        else: result = cursor.fetchmany()
        conn.commit()

        # Closing database
        cursor.close()
        conn.close()
        logging.debug(f'Executed request "{request}" with parameters "{str(param)}", that returned "{str(result)}"')
        if result: return result
        else: return None

    except sqlite3.Error as error:
        logging.error(f'Database error: {error}')
        return None
