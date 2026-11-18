// npm install --prefix outputs/KMB_20MB/deps meshoptimizer@1.3.0
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

const manifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const { MeshoptSimplifier } = await import(pathToFileURL(manifest.module).href);
await MeshoptSimplifier.ready;
const results = [];
for (const job of manifest.jobs) {
  const bytes = fs.readFileSync(job.input);
  const data = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  const [vertexCount, indexCount] = new Uint32Array(data, 0, 2);
  const vertices = new Float32Array(data, 8, vertexCount * 11);
  const indices = new Uint32Array(data, 8 + vertices.byteLength, indexCount);
  const attributes = new Float32Array(vertexCount * 5);
  const locks = new Uint8Array(vertexCount);
  for (let i = 0; i < vertexCount; i++) {
    attributes.set(vertices.subarray(i * 11 + 3, i * 11 + 8), i * 5);
  }
  // Keep each mesh's extremes, so body and wheel bounds do not jump at a switch.
  for (let axis = 0; axis < 3; axis++) {
    let min = 0, max = 0;
    for (let i = 1; i < vertexCount; i++) {
      if (vertices[i * 11 + axis] < vertices[min * 11 + axis]) min = i;
      if (vertices[i * 11 + axis] > vertices[max * 11 + axis]) max = i;
    }
    locks[min] = locks[max] = 1;
  }
  const [reduced, error] = MeshoptSimplifier.simplifyWithAttributes(
    indices, vertices, 11, attributes, 5, [0.2, 0.2, 0.2, 0.5, 0.5], locks,
    Math.max(12, Math.floor(indexCount * job.ratio / 3) * 3), job.error,
    ['ErrorAbsolute', 'LockBorder']);
  fs.writeFileSync(job.output, Buffer.from(reduced.buffer, reduced.byteOffset, reduced.byteLength));
  results.push({ id: job.id, indices: reduced.length, error_m: error });
}
fs.writeFileSync(manifest.result, JSON.stringify(results));
