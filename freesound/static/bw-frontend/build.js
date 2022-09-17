// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

const inquirer = require('inquirer');
const shell = require('shelljs');

const pages = [
  'front',
  'browse',
  'sound',
  'pack',
  'profile',
  'followers',
  'following',
  'tagsFollowing',
  'editprofile',
  'editprofilepassword',
  'editprofilenotifications',
  'editprofilecloseaccount',
  'forumshot',
  'forummostcommented',
  'forumlists',
  'forumliststhread',
  'forumthread',
  'forumnewthread'
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

// @license-end
