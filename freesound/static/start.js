const inquirer = require('inquirer')
const shell = require('shelljs')

const start = async () => {
  const answers = await inquirer.prompt([
    {
      type: 'list',
      name: 'pagename',
      message: 'Which page would you like to open?',
      choices: ['Front', 'Search'],
      filter: val => val.toLowerCase(),
    },
  ])
  shell.exec(`parcel freesound/static/html/${answers.pagename}.njk`)
}

start()
