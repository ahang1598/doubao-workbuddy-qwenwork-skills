const MiniCssExtractPlugin = require('mini-css-extract-plugin');

module.exports = {
  devtool: 'source-map',
  module: {
    rules: [
      { test: /\.tsx?$/, exclude: /node_modules/, use: [{ loader: 'ts-loader' }] },
      { test: /\.css$/, use: [MiniCssExtractPlugin.loader, 'css-loader'] },
      { test: /\.png$/i, type: 'asset/resource' },
    ],
  },
  plugins: [new MiniCssExtractPlugin({ filename: '[name].css' })],
  resolve: { extensions: ['.ts', '.tsx', '.js', '.json'] },
};
