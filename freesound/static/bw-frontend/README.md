# Freesound Beast Whoosh Front end development

## Installation

Checkout the Freesound repository and run this command from the root folder:

```
npm install
```

## Building static

Checkout the Freesound repository and run this command from the root folder:

```
npm run build
```


## Icons

This project uses https://icomoon.io for generating the icon font.
To update icons:

* Open iconmoon app in web browser
* Import `bw-icons/selection.json` file
* Add/modify icons using the online editor
* Go to "generate font", it will complain that "Strokes get ignored when generating fonts. You can convert them to fills to prevent this.", say "Continue"
* Click "download". A compressed folder will be downloaded which wou use to replace whole bw-icons folder from this directory.
* Check the differences in `bw-icons/style.css` after you replaced folder contents, and make sure you copy code bits from old `style.css` that were added manually to the new version (the diff editor will make thos changes very clear).

## Running the new frontend in Django

Checkout [this wiki page](https://github.com/MTG/freesound/wiki/Working-with-static-files-%28Beast-Whoosh-front-end%29) for info about working with the new frontend static files and Django.
