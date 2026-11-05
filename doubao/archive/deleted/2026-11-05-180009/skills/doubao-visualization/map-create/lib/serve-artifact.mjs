import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { basename, dirname, resolve } from 'node:path';

export async function serveArtifact(htmlFile, manifest) {
  const names = new Set([
    basename(htmlFile),
    ...Object.values(manifest.assets)
      .map(asset => asset.url)
      .filter(url => basename(url) === url),
  ]);
  const server = createServer(async (request, response) => {
    const name = decodeURIComponent(
      new URL(request.url, 'http://localhost').pathname.slice(1),
    );
    if (!names.has(name) || request.method !== 'GET') {
      response.writeHead(404).end();
      return;
    }
    try {
      const bytes = await readFile(resolve(dirname(htmlFile), name));
      const mime = {
        html: 'text/html',
        js: 'text/javascript',
        css: 'text/css',
        json: 'application/json',
      };
      response.writeHead(200, {
        'content-type':
          mime[name.split('.').at(-1)] || 'application/octet-stream',
      });
      response.end(bytes);
    } catch {
      response.writeHead(404).end();
    }
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  return {
    url:
      'http://127.0.0.1:' +
      server.address().port +
      '/' +
      encodeURIComponent(basename(htmlFile)),
    close: () =>
      new Promise(resolve => {
        server.closeAllConnections();
        server.close(resolve);
      }),
  };
}
