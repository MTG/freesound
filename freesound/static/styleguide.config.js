const path = require('path')


module.exports = {
  webpackConfig: require('./webpack/webpack.config'),
  require: [
    path.join(__dirname, 'src/base'),
  ],
  theme: {
    color: {
      link: '#FF3546',
      linkHover: '#FF4958'
    },
  },
  sections: [
    {
      name: 'Introduction',
      content: 'styleguide/introduction.md',
    },
    {
      name: 'UI components',
      sections: [
        {
          name: 'Buttons',
          content: 'styleguide/buttons.md',
        },
      ],
    },
  ],
};
