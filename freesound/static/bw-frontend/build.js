const { Parcel } = require('@parcel/core');
const fs = require('node:fs');
const path = require('node:path');

const projectDir = __dirname;
const distDir = path.join(projectDir, 'dist');

const entries = [
  path.join(projectDir, 'src/index.js'),
  path.join(projectDir, 'src/index-dark.js'),
  path.join(projectDir, 'src/pages/*.js'),
];

const cleanDist = () => {
  if (fs.existsSync(distDir)) {
    fs.rmSync(distDir, { recursive: true, force: true });
  }
};

const build = async () => {
  const bundler = new Parcel({
    entries,
    defaultConfig: '@parcel/config-default',
    defaultTargetOptions: {
      distDir,
      publicUrl: '/static/bw-frontend/dist',
      sourceMaps: true,
    },
    mode: 'production',
    shouldDisableCache: false,
    env: {
      NODE_ENV: 'production',
    },
  });

  try {
    cleanDist();
    console.log('⚙️  Building frontend assets with Parcel...');
    const { bundleGraph, buildTime } = await bundler.run();
    const bundles = bundleGraph.getBundles();
    console.log(`✅ Build complete in ${(buildTime / 1000).toFixed(2)}s (${bundles.length} bundles output)`);
  } catch (error) {
    console.error('❌ Build failed');
    console.error(error);
    process.exitCode = 1;
  }
};

build();
