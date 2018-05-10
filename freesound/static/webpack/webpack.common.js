const path = require('path');

const SUPPORTED_BROWSERS = ['>1%', 'last 4 versions', 'Firefox ESR', 'not ie < 10'];

module.exports = {
  entries: {
    base: path.join(__dirname, '..', 'base.js'),
    index: path.join(__dirname, '..', 'src/common.js'),
    front: path.join(__dirname, '../src/pages/front.js'),
    search: path.join(__dirname, '../src/pages/search.js'),
  },
  output: {
    filename: '[name].js',
    path: path.join(__dirname, '..', 'dist'),
    pathinfo: true,
    devtoolModuleFilenameTemplate: info =>
      path
        .relative(path.join(__dirname, '..', 'src'), info.absoluteResourcePath)
        .replace(/\\/g, '/'),
  },
  loaders: {
    jsLoader: {
      test: /\.js$/,
      exclude: /node_modules/,
      use: {
        loader: 'babel-loader',
        options: {
          presets: [
            [
              'env',
              {
                targets: {
                  browsers: SUPPORTED_BROWSERS,
                },
              },
            ],
          ],
        },
      },
    },
    postCssLoader: {
      loader: 'postcss-loader',
      options: {
        // Necessary for external CSS imports to work
        // https://github.com/facebookincubator/create-react-app/issues/2677
        ident: 'postcss',
        plugins: () => [
          require('postcss-flexbugs-fixes'),
          require('autoprefixer')({
            browsers: SUPPORTED_BROWSERS,
            flexbox: 'no-2009',
          }),
        ],
      },
    },
    fileLoader: {
      test: /\.svg$/,
      exclude: /icons/,
      loaders: ['file-loader'],
    },
    iconsLoader: {
      test: /\.svg$/,
      include: /icons/,
      loaders: ['raw-loader'],
    },
  },
};
