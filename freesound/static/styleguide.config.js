module.exports = {
  webpackConfig: require('./webpack/webpack.config.dev.js'),
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
          components: () => ['src/setup.js', 'styleguide/styleguideSetup.js'],
        },
      ],
    },
  ],
};
