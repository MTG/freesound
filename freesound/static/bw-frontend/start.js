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
        'ForumNewthread',
        'MessagesInbox', 
        'MessagesNew'
      ],
      filter: val => val.toLowerCase(),
    },
  ]);
  shell.exec(`parcel serve freesound/static/bw-frontend/html/${answers.pagename}.njk -d ${outDir}`);
};

start();
