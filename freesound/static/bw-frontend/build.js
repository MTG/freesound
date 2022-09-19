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
  'forumnewthread',
  'messagesinbox', 
  'messagesnew'
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
