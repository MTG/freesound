# Freesound Frontend Styleguide

This page is meant to provide guidelines on how to start and use the front-end code of the project
and moreover on how to use the developed "components" (we are not using react but I'll still refer
to the atoms of the design as components for simplicity).

## Installation

Run `npm install` to install all the dependencies. A bunch of useful scripts:

* `npm run prettier`: to automatically format all the `.js` files with prettier
* `npm run eslint`: to automatically detect problems in the js code (using the airbnb-base eslint
  configuration)

### How to run this styleguide locally

Simply run `npm run styleguide`.

## Build static files

You have several options:

* `npm start`: to start a node.js dev server with hot reloading. Meant to be used for front end
  development only
* `npm run build`: to compile a non-minified bundle, with sourcemaps. You should use this while
  you're developing python stuff.
* `npm run build:prod`: to generate a minified bundle. This should be your choice in production.

You will find all the generated files inside the folder `freesound/static/dist`. The ones generated
with `build:prod` will have the `.min` suffix.

## Styles
This project uses the grid system from Bootstrap 4, with custom variables.
Classnames follow the [BEM](http://getbem.com/naming/) convention, while the folder structure is inspired by [ITCSS](https://www.xfive.co/blog/itcss-scalable-maintainable-css-architecture/).

## Some tips on this styleguide
Each component has a `View code` at its bottom. You can click it to check the HTML code of the component.
