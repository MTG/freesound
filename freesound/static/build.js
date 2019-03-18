const inquirer = require('inquirer')
const shell = require('shelljs')

const pages = ['front', 'browse']

const outDir = 'freesound/static/dist'

const start = async () => {
  pages.forEach(page => {
    shell.exec(`parcel build freesound/static/html/${page}.njk -d ${outDir}`)
  })
}

start()
