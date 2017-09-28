# freesound front-end code

## Overview
The main components we use are:
* [Babel](https://babeljs.io) to convert JSX files into JS and ES6 into ES5 (ES6 support among browsers is still incomplete at the time of writing, March '16)
* [webpack](https://webpack.github.io/) to automatize development tasks, such as compilation with babel and compilation of SCSS code. In addition, webpack provides *hot reloading* that allows the page to automatically reload when changes in its JS/CSS code are detected.
* [Autoprefixer](https://github.com/postcss/autoprefixer) to automatically add vendor prefixes to CSS rules


## Installation
Ensure you have node.js and npm installed before proceeding.

Run:

    npm install

on the ```freesound/freesound/static``` folder to automatically install all the remaining dependencies.

## Development
Run:

    npm run dev

to start the webpack-dev-server. This server (running at the port 8080) serves the assets files while providing the *hot reloading* functionality at the same time.

**All the source files used during development must be in the folder** ```freesound/freesound/build/src```.

 **Important:** make sure that your IDE/text editor is running an ESlinter and using the file ```freesound/freesound/build/.eslintsrc``` as its configuration. This will ensure that we follow the Airbnb style guides.

## Production
Run:

    npm run deploy

To generate the static files that will be used in production. The output of this compilation will be stored in the folder ```freesound/freesound/build/js``.

**Important**: make sure that your templates files automatically load static files from the right location, according to the environment. We recommend using Django templates tag in this way:
```python
# in your view method
if settings.USE_JAVASCRIPT_DEVELOPMENT_SERVER:
    context['debug_cdn'] = True
return render(request, 'your/template/html', context)
```
```
// in your template file
{% if debug_cdn %}
    <script src="http://localhost:8080/js/*jsfile*.js"></script>
{% else %}
    <script src="{% static 'js/*jsfile*.js' %}"></script>
{% endif %}
```
## Eslint
Run:
```
npm run eslint
```
To lint the JS code according to the AirBnb code style guide.

### Continuous Integration
Jenkins runs both the commands for tests and eslint. Make sure both of them are not failing before each commit on the master branch.
