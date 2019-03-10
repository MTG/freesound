const inquirer = require('inquirer')
const shell = require('shelljs')

const pages = ['front', 'browse']

const start = async () => {
  pages.forEach(page => {
    shell.exec(`parcel build freesound/static/html/${page}.njk`)
  })
}

start()
