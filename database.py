#database.py

import duckdb

con = duckdb.connect(database=':memory:')

def get_connection():
    return con