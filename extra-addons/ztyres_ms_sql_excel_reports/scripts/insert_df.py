import pandas as pd
from sqlalchemy import create_engine, text

def df_to_postgres(df, table_name, database_url='postgresql://ztyres:ztyres@192.168.1.3:5632/reports'):
    """
    This function will:
    1. Check if the database exists, if not create it.
    2. Delete the table if it exists in the PostgreSQL database.
    3. Create a new table.
    4. Insert the data from the DataFrame into the table.
    """
    # Extracting database name

    
    # Connection to the PostgreSQL server without specifying a database
    engine_server = create_engine('/'.join(database_url.split('/')[:-1]))


    
    # Disposing the engine as soon as we're done with it
    engine_server.dispose()
    
    # Create an engine instance for the specified database
    engine = create_engine(database_url)
    
    
    # Use pandas to create the table and insert the data
    df.to_sql(table_name, engine, if_exists='replace', index=False)
    
    # Disposing the engine after operations
    engine.dispose()
