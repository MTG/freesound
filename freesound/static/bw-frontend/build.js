const inquirer = require('inquirer');
const shell = require('shelljs');

const outDir = 'freesound/static/bw-frontend/dist';
const outDirDarkMode = 'freesound/static/bw-frontend/dist-dark';


// Copy public files to dist folder
shell.exec(
  `parcel build freesound/static/bw-frontend/public/*.* -d ${outDir}`
);

// Build main js and css files
shell.exec(
  `echo "\\$color-theme: 'light';" > freesound/static/bw-frontend/styles/variables/color-theme.scss && parcel build freesound/static/bw-frontend/src/index.js -d ${outDir}`
);

// Build page-specific js files
shell.exec(
  `parcel build freesound/static/bw-frontend/src/pages/*.js -d ${outDir}`
);

// Build dark-mode css
// Now build again js and css for the dark mode
// 1) Build them in a different directory
// 2) Copy the generated css files (js is not relevant)
// 3) Remove that extra directory
shell.exec(
  `echo "\\$color-theme: 'dark';" > freesound/static/bw-frontend/styles/variables/color-theme.scss && parcel build freesound/static/bw-frontend/src/index.js -d ${outDirDarkMode} && cp ${outDirDarkMode}/index.css ${outDir}/index-dark.css && cp ${outDirDarkMode}/index.map ${outDir}/index-dark.map && rm -r ${outDirDarkMode}`
);
