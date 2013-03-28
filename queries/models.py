from django.db import models

class Query(models.Model):
	querytext = models.CharField(max_length=200, primary_key=True)
	# Count the number of times the query has been requested
	frequency = models.IntegerField(default=0)

	def __unicode__(self):
		return self.querytext
