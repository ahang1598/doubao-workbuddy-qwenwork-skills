module.exports = {
  entry: './src/main.ts',
  target: 'electron-main',
  devtool: 'source-map',
  module: {
    rules: [
      { test: /\.tsx?$/, exclude: /node_modules/, use: [{ loader: 'ts-loader' }] },
      { test: /\.png$/i, type: 'asset/resource' },
    ],
  },
  resolve: { extensions: ['.ts', '.tsx', '.js', '.json'] },
  externals: { 'uiohook-napi': 'commonjs2 uiohook-napi' },
};
