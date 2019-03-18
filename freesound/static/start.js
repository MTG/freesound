const inquirer = require('inquirer')
const shell = require('shelljs')

const outDir = 'freesound/static/dist'

const start = async () => {
  const answers = await inquirer.prompt([
    {
      type: 'list',
      name: 'pagename',
      message: 'Which page would you like to open?',
      choices: ['Front', 'Browse'],
      filter: val => val.toLowerCase(),
    },
  ])
  shell.exec(`parcel serve freesound/static/html/${answers.pagename}.njk -d ${outDir}`)
}

start()
