from django.conf.urls.defaults import *
from manager.views import list_indexes

urlpatterns = patterns('',
    # Example:
    # (r'^persistence/', include('persistence.foo.urls')),
    
    url(r'indexes/?', list_indexes, name='indexes'),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)
