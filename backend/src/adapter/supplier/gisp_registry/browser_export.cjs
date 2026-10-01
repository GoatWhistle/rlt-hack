const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const directory = path.resolve(process.argv[2] || '/tmp/gisp-snapshot');
const onlyOrganizations = process.argv.includes('--organizations-only');
const source = 'https://gisp.gov.ru';
const format = 'gisp-browser-snapshot-v1';
const sha = (value) => crypto.createHash('sha256').update(value).digest('hex');
async function fileSha(file) {
  const digest = crypto.createHash('sha256');
  for await (const chunk of fs.createReadStream(file)) digest.update(chunk);
  return digest.digest('hex');
}

async function collect(page, name, kind, size, parallel) {
  const target = path.join(directory, `${name}.jsonl`);
  const partial = `${target}.partial`;
  const checkpoint = `${target}.checkpoint.json`;
  await page.goto(`${source}/pp719v2/pub/${kind}/`, { waitUntil: 'commit', timeout: 120000 });
  await page.waitForTimeout(4000);
  async function request(skip, take, count) {
    return page.evaluate(async ({ kind, skip, take, count }) => {
      const response = await fetch(`/pp719v2/pub/${kind}/b/`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ opt: { skip, take, requireTotalCount: count } }),
      });
      if (!response.ok || !(response.headers.get('content-type') || '').includes('json')) {
        throw new Error(`${kind} ${skip}: HTTP ${response.status} ${response.headers.get('content-type')}`);
      }
      const data = await response.json();
      if (data.ok !== true || !Array.isArray(data.items)) throw new Error(`${kind} ${skip}: invalid JSON`);
      return data;
    }, { kind, skip, take, count });
  }
  const first = await request(0, size, true);
  const total = first.total_count;
  if (!Number.isInteger(total) || total < 1 || first.items.length !== Math.min(size, total)) {
    throw new Error(`${kind}: invalid first page or total`);
  }
  const firstHash = sha(JSON.stringify(first.items));
  let state;
  if (fs.existsSync(target)) {
    const saved = JSON.parse(fs.readFileSync(`${target}.complete.json`, 'utf8'));
    if (saved.total !== total || saved.firstHash !== firstHash) throw new Error(`${kind}: completed data changed`);
    const digest = await fileSha(target);
    if (saved.sha256 && saved.sha256 !== digest) throw new Error(`${kind}: completed file hash changed`);
    if (!saved.sha256) fs.writeFileSync(`${target}.complete.json`, JSON.stringify({ ...saved, sha256: digest }), { mode: 0o600 });
    return { count: total, sha256: digest };
  }
  if (fs.existsSync(checkpoint)) {
    state = JSON.parse(fs.readFileSync(checkpoint, 'utf8'));
    if (state.total !== total || state.firstHash !== firstHash) throw new Error(`${kind}: source changed since checkpoint`);
    fs.truncateSync(partial, state.fileSize);
  } else {
    fs.writeFileSync(partial, '', { mode: 0o600 });
    state = { total, firstHash, nextOffset: 0, count: 0, fileSize: 0 };
  }
  const handle = fs.openSync(partial, 'a');
  try {
    for (let start = state.nextOffset; start < total; start += size * parallel) {
      const offsets = [];
      for (let offset = start; offset < Math.min(start + size * parallel, total); offset += size) offsets.push(offset);
      const pages = await Promise.all(offsets.map((offset) => offset === 0 ? first : request(offset, size, false)));
      let block = '';
      for (let index = 0; index < pages.length; index++) {
        const expected = Math.min(size, total - offsets[index]);
        if (pages[index].items.length !== expected) throw new Error(`${kind} ${offsets[index]}: incomplete page`);
        for (const item of pages[index].items) block += `${JSON.stringify(item)}\n`;
        state.count += pages[index].items.length;
      }
      if (fs.writeSync(handle, block) !== Buffer.byteLength(block)) throw new Error(`${kind}: partial file write`);
      fs.fsyncSync(handle);
      state.fileSize += Buffer.byteLength(block);
      state.nextOffset = offsets.at(-1) + size;
      fs.writeFileSync(`${checkpoint}.next`, JSON.stringify(state), { mode: 0o600 });
      fs.renameSync(`${checkpoint}.next`, checkpoint);
      if (state.count % 10000 === 0 || state.count === total) console.log(`${name}: ${state.count}/${total}`);
    }
  } finally {
    fs.closeSync(handle);
  }
  const last = await request(0, size, true);
  if (last.total_count !== total || sha(JSON.stringify(last.items)) !== firstHash || state.count !== total) {
    throw new Error(`${kind}: source changed during crawl`);
  }
  fs.renameSync(partial, target);
  const digest = await fileSha(target);
  fs.writeFileSync(`${target}.complete.json`, JSON.stringify({ total, firstHash, sha256: digest }), { mode: 0o600 });
  fs.unlinkSync(checkpoint);
  return { count: total, sha256: digest };
}

(async () => {
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const browser = await chromium.launch({ headless: false, channel: 'chrome' });
  try {
    const page = await browser.newPage();
    const organizations = await collect(page, 'organizations', 'org', 1000, 1);
    if (onlyOrganizations) return;
    const products = await collect(page, 'products', 'prod', 100, 4);
    fs.writeFileSync(path.join(directory, 'manifest.json'), JSON.stringify({
      format,
      source: `${source}/pp719v2/pub/`,
      completed_at: new Date().toISOString(),
      organizations,
      products,
    }, null, 2), { mode: 0o600 });
    console.log(`COMPLETE ${directory}`);
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(`FAILED ${error.message}`); process.exitCode = 1; });
