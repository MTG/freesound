const path = require('path');
const webpack = require('webpack');
const autoprefixer = require('autoprefixer');
const precss = require('precss');
const jsonImporter = require('node-sass-json-importer');

function getEntrySources(sources) {
  if (process.env.NODE_ENV !== 'production') {
    sources.push('webpack-dev-server/client?http://localhost:8080');
  }
  return sources;
}

function getPlugins(plugins) {
  if (process.env.NODE_ENV !== 'production') {
    plugins.push(
      new webpack.HotModuleReplacementPlugin(),
      new webpack.NoErrorsPlugin());
  }
  return plugins;
}

const config = {
  entry: {
    index: getEntrySources([
      './freesound/static/src/js/index',
    ]),
  },
  output: {
    filename: './freesound/static/dist/js/[name].js',
  },
  plugins: getPlugins([
    new webpack.DefinePlugin({
      'process.env': {
        NODE_ENV: JSON.stringify(process.env.NODE_ENV),
      },
    }),
  ]),
  module: {
    loaders: [
      {
        test: /\.jsx?$/,
        loaders: ['babel'],
        include: [
          path.resolve(__dirname, 'src'),
        ],
      },
      {
        test: /\.scss$/,
        loaders: [
          'style',
          'css',
          'postcss',
          'sass',
        ],
        include: [
          path.resolve(__dirname, 'src/stylesheet'),
          path.resolve(__dirname, 'src/components'),
        ],
      },
      {
        test: /\.css$/,
        loaders: [
          'style',
          'css',
        ],
      },
      {
        test: /\.(png|jpg|svg)$/,
        loader: 'file?name=[name].[ext]',
      },
    ],
  },
  resolve: {
    extensions: ['', '.js', '.jsx'],
  },
  postcss() {
    return [autoprefixer, precss];
  },
  sassLoader: {
    // Apply the JSON importer via sass-loader's options.
    importer: jsonImporter,
  },
};

module.exports = config;
