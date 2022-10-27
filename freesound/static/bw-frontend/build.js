const inquirer = require('inquirer');
const shell = require('shelljs');

const outDir = 'freesound/static/bw-frontend/dist';

// Copy public files to dist folder
shell.exec(
  `parcel build freesound/static/bw-frontend/public/*.* -d ${outDir}`
);
// Build main js and css files
shell.exec(
  `parcel build freesound/static/bw-frontend/src/index.js -d ${outDir}`
);
// Build page-specific js files
shell.exec(
  `parcel build freesound/static/bw-frontend/src/pages/*.js -d ${outDir}`
);