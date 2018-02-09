const path = require('path');

module.exports = {
  webpackConfig: require('./webpack/webpack.config'),
  require: [path.join(__dirname, 'base')],
  theme: {
    color: {
      link: '#FF3546',
      linkHover: '#FF4958',
    },
  },
  styles: {
    TabButton: {
      button: {
        position: 'relative',
        padding: '14px 30px',
        textTransform: 'none',
      },
    },
    Heading: {
      heading: {
        margin: '10px 0 20px',
      },
    },
  },
  sections: [
    {
      name: 'Introduction',
      content: 'styleguide/introduction.md',
    },
    {
      name: 'Atoms',
      sections: [
        {
          name: 'Buttons',
          content: 'styleguide/atoms/buttons.md',
        },
        {
          name: 'Links',
          content: 'styleguide/atoms/links.md',
        },
      ],
    },
    {
      name: 'Molecules',
      sections: [
        {
          name: 'Navbar',
          content: 'styleguide/molecules/navbar.md',
        },
      ],
    },
  ],
};
