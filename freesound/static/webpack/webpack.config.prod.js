const webpack = require('webpack');
const ExtractTextPlugin = require('extract-text-webpack-plugin');

const common = require('./common');

module.exports = {
  devtool: false,
  entry: common.entries,
  output: Object.assign({}, common.output, {
    filename: '[name].min.js',
    pathinfo: false,
  }),
  bail: true,
  module: {
    loaders: [
      common.loaders.jsLoader,
      {
        test: /\.s?css$/,
        loader: ExtractTextPlugin.extract({
          fallback: 'style-loader',
          use: [
            {
              loader: 'css-loader',
              options: {
                minimize: true,
              },
            },
            common.loaders.postCssLoader,
            'sass-loader',
          ],
          publicPath: '',
        }),
      },
    ],
  },
  plugins: [
    new ExtractTextPlugin({
      filename: 'styles.min.css',
    }),
    new webpack.optimize.UglifyJsPlugin({
      compress: {
        warnings: false,
        // Disabled because of an issue with Uglify breaking seemingly valid code:
        // https://github.com/facebookincubator/create-react-app/issues/2376
        // Pending further investigation:
        // https://github.com/mishoo/UglifyJS2/issues/2011
        comparisons: false,
      },
      output: {
        comments: false,
        // Turned on because emoji and regex is not minified properly using default
        // https://github.com/facebookincubator/create-react-app/issues/2488
        ascii_only: true,
      },
      sourceMap: false,
    }),
    new webpack.EnvironmentPlugin({
      NODE_ENV: 'production',
      BROWSER: true,
    }),
  ],
};
