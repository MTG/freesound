# Instructions for working with static files

Ensure you have node.js and `npm` installed before proceeding.
Run:

    npm install

on the ```static``` folder to automatically install all the remaining
dependencies.

## Development
Run:

    npm run dev

to start the webpack-dev-server. This server (running at the port 8080)
serves the assets files while providing the *hot reloading* functionality
at the same time. Source files for static files are in ```static/src```.

You can chose whether the Django template will load the static files from
the development server or from disc by setting the `USE_JS_DEVELOPMENT_SERVER`
parameter. By default, `USE_JS_DEVELOPMENT_SERVER` will be set to `True`
when running the Django application in `DEBUG` mode.


## Production
Run:

    npm run deploy

This will generate the static files that will be used in production and
store them in the folder ```static/dist```. Generated distribution files
should not be added to the git repository. The deployment scripts take
care of generating the static files and copying them to the servers.

