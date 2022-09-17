// @license magnet:?xt=urn:btih:0b31508aeb0634b347b8270c7bee4d411b5d4109&dn=agpl-3.0.txt AGPL-v3-or-later

const inquirer = require('inquirer');
const shell = require('shelljs');

const outDir = 'freesound/static/bw-frontend/dist';

const start = async () => {
  const answers = await inquirer.prompt([
    {
      type: 'list',
      name: 'pagename',
      message: 'Which page would you like to open?',
      choices: [
        'Front',
        'Browse',
        'Profile',
        'Sound',
        'Pack',
        'Followers',
        'Following',
        'TagsFollowing',
        'EditProfile',
        'EditProfilePassword',
        'EditProfileNotifications',
        'EditProfileCloseAccount',
        'ForumsHot',
        'ForumMostCommented',
        'ForumLists',
        'ForumListsThread',
        'ForumThread',
        'ForumNewthread'
      ],
      filter: val => val.toLowerCase(),
    },
  ]);
  shell.exec(`parcel serve freesound/static/bw-frontend/html/${answers.pagename}.njk -d ${outDir}`);
};

start();

// @license-end
