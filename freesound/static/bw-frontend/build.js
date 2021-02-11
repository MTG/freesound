const inquirer = require('inquirer');
const shell = require('shelljs');

const pages = [
  'front',
  'browse',
  'sound',
  'forumshot',
  'forummostcommented',
  'forumlists',
  'forumliststhread',
  'forumthread',
  'forumnewthread',
];

const outDir = 'freesound/static/bw-frontend/dist';

const start = async () => {
  pages.forEach(page => {
    shell.exec(
      `parcel build freesound/static/bw-frontend/html/${page}.njk -d ${outDir}  --no-content-hash`
    );
  });
};

start();
