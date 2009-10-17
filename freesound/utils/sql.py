from django.db import connection

class DelayedQueryExecuter:
    """ The delayed executed executes a query, but waits for the first time
    the results are actually needed, i.e. via iteration """
    def __init__(self, query):
        self.query = query
        self.cache = None
    
    def __iter__(self):
        if self.cache is None:
            cursor = connection.cursor() #@UndefinedVariable
            cursor.execute(self.query)
            
            column_names = [desc[0] for desc in cursor.description]
            
            # cursor.fetchall fetches all results in one go (i.e. not a generator) so this is just as fast
            self.cache = (dict(zip(column_names, row)) for row in cursor.fetchall())

        for row in self.cache:
            yield row