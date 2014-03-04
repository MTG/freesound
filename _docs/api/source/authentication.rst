.. _authentication:

Authentication (APIv2)
<<<<<<<<<<<<<<<<<<<<<<

APIv2 offers two authentication strategies: Token based authentication and OAuth2.

Token based authentication is the simplest one as it only requires the developer to request an API key
(http://www.freesound.org/apiv2/apply) and add this key to all requests (see below).
The flow for OAuth2 authentication is a little bit more complicated but it allows users to log in in Freesound
from your application. This enables non "read-only" resources such as uploading or rating sounds.
Most of the resources are accessible using both authentication strategies but some of them
are restricted to the use of OAuth2. These resources are marked as "OAuth2 required" in the :ref:`resources` page.



Token authentication
=========================================================

To authenticate API calls with the token strategy you'll need to create a Freesound account (if you don't have one yet!)
and request new API credentials key by visiting http://www.freesound.org/apiv2/apply.
In this page you'll see a table with all API keys you have requested plus some other information. You should use
the keys in 'Client secret/Api key' column, which are long alphanumeric strings that look like this:
36e256ba563187f86eed608u13cacd520czd017e.
You should get a different API key for every
application you develop.

Once you have an API key you will need to add it to every request you make to the API. You can do that either by
adding the key as a ``token`` GET parameter...

::

  curl "http://www.freesound.org/apiv2/search/?query=piano&token=YOUR_API_KEY

...or by adding it as an authorization header:

::

  curl -H "Authorization: Token YOUR_API_KEY" "http://www.freesound.org/apiv2/search/?query=piano"

And there we go, that's all you need to know about token authentication!

.. _oauth-authentication:

OAuth2 authentication
=========================================================

To authenticate API calls with OAuth2 you'll also need to create a Freesound account (if you don't have one yet!)
and request new API credentials by visiting http://www.freesound.org/apiv2/apply. Our OAuth2 implementation
follows the 'authorization code grant' flow described in the RFC6749 (http://tools.ietf.org/html/rfc6749). That flow
basically consists in three steps:

* Step 1: Your application redirects users to a Freesound page where they log in and are asked to give permissions to your application.

* Step 2: If users grant access to your application, Freesound redirects users to a url you provide and includes an authorization grant as a GET parameter*.

* Step 3: Your application uses that authorization grant to request an access token that 'links' the end user with your application and that you will then add to all your API requests.

*If your application can't handle requests, the user can also be redirected to another Freesound page that prints the
authorization grant on screen so that the user can manually introduce it in your application (see below).

All these steps and all other further OAuth2 API requests **need to be done using https**.

Step 1
------

You should redirect user to the following url...

::

  https://www.freesound.org/apiv2/oauth2/authorize/

... including as GET parameters:

======================  ========================================================================
Name                    Description
======================  ========================================================================
``client_id``           Client id of your API credential (not the client secret!)
``response_type``       Must be 'code'
``state``               Arbitrary string that will be included in the redirect call. This parameter is **not required**.
======================  ========================================================================

Example:

::

  https://www.freesound.org/apiv2/oauth2/authorize/?client_id=YOUR_CLIENT_ID&response_type=code&state=xyz


In this page users will be prompted to log in into Freesund (if they are not already logged in) and will be asked to give
permission to your application to access their data and act on their behalf.