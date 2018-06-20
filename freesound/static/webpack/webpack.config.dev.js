const path = require('path');
const webpack = require('webpack');
const HtmlWebpackPlugin = require('html-webpack-plugin');

const common = require('./webpack.common');

module.exports = {
  devtool: 'cheap-module-source-map',
  entry: common.entries,
  output: common.output,
  module: {
    loaders: [
      common.loaders.jsLoader,
      {
        test: /\.s?css$/,
        use: [
          'style-loader',
          'css-loader',
          common.loaders.postCssLoader,
          'sass-loader',
          'import-glob-loader',
        ],
      },
      common.loaders.fileLoader,
      common.loaders.iconsLoader,
    ],
  },
  plugins: [
    // enable HMR globally
    new webpack.HotModuleReplacementPlugin(),
    new HtmlWebpackPlugin({
      title: 'Freesound index',
      filename: 'index.html',
      template: path.join(__dirname, '..', 'dev-templates/index.html'),
      chunks: ['base', 'index'],
    }),
    new HtmlWebpackPlugin({
      title: 'Front page',
      filename: 'front.html',
      template: path.join(__dirname, '..', 'dev-templates/front.html'),
      chunks: ['base', 'index', 'front'],
    }),
    new HtmlWebpackPlugin({
      title: 'Search',
      filename: 'search.html',
      template: path.join(__dirname, '..', 'dev-templates/search.html'),
      chunks: ['base', 'index', 'search'],
    }),
  ],
  devServer: {
    hot: true,
    host: 'localhost',
    port: 3000,
    open: true,
    openPage: 'index.html',
    contentBase: path.join(__dirname, '..', 'public'),
  },
};
