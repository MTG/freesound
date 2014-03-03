.. _authentication:

Authentication (APIv2)
<<<<<<<<<<<<<<<<<<<<<<

APIv2 offers two authentication strategies: Token based authentication and OAuth.

Token based authentication is the simplest one as it only requires the developer to request an API key
(http://www.freesound.org/apiv2/apply) and add this key to all requests (see below).
The flow for OAuth authentication is a little bit more complicated but it allows users to log in in Freesound
from your application. This enables non "read-only" resources such as uploading or rating sounds.
Most of the resources are accessible using both authentication strategies but some of them
are restricted to the use of OAuth. These resources are marked as "OAuth required" in the :ref:`resources` page.



Token authentication
=========================================================



.. _oauth-authentication:

OAuth authentication
=========================================================