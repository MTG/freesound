from django.db import models

class Query(models.Model):
	querytext = models.CharField(max_length=200, unique=True, db_index=True)
	# Count the number of times the query has been requested
	frequency = models.IntegerField(default=0, db_index=True)

	def __unicode__(self):
		return self.querytext
