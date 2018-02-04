const webpack = require('webpack');
const ExtractTextPlugin = require('extract-text-webpack-plugin');

const common = require('./webpack.common');

module.exports = {
  devtool: 'source-map',
  entry: common.entries,
  output: common.output,
  module: {
    loaders: [
      common.loaders.jsLoader,
      {
        test: /\.s?css$/,
        loader: ExtractTextPlugin.extract({
          fallback: 'style-loader',
          use: ['css-loader', common.loaders.postCssLoader, 'sass-loader', 'import-glob-loader'],
          publicPath: '',
        }),
      },
    ],
  },
  plugins: [
    new ExtractTextPlugin({
      filename: 'styles.css',
    }),
    new webpack.EnvironmentPlugin({
      NODE_ENV: 'production',
      BROWSER: true,
    }),
  ],
};