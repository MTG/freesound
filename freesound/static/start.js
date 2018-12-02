const inquirer = require('inquirer')
const { exec } = require('child_process')

inquirer
  .prompt([
    {
      type: 'list',
      name: 'pagename',
      message: 'Which page would you like to open?',
      choices: ['Front', 'Search'],
      filter: val => val.toLowerCase(),
    },
  ])
  .then(answers => {
    exec(`parcel freesound/static/html/${answers.pagename}.njk`)
    console.log('Your page is ready at http://localhost:1234')
  })
