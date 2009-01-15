from django.db import connection

class DelayedQueryExecuter:
    def __init__(self, query):
        self.query = query
        
    def __iter__(self):
        cursor = connection.cursor()
        cursor.execute(self.query)
        collumn_names = [desc[0] for desc in cursor.description]
        for row in cursor.fetchall():
            yield dict(zip( collumn_names, row))
