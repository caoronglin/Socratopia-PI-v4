// A real embedded Pi SDK session, not an independent prompt emulation.
import { createServer } from 'node:http';
import { timingSafeEqual } from 'node:crypto';
import { existsSync, lstatSync, mkdirSync, realpathSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { createAgentSession, SessionManager } from '@earendil-works/pi-coding-agent';

const token = process.env.SOCRATOPIA_API_TOKEN;
if (!token || token.length < 16) {
  throw new Error('Set SOCRATOPIA_API_TOKEN (at least 16 characters) before starting Pi');
}
const activeSessions = new Set();
const busy = new Set();
const maxConcurrent = 4;
const maxBytes = 32 * 1024;
const cwd = resolve(process.env.SOCRATOPIA_ROOT || process.cwd());

// Pi SDK sessions are private to a course, not a single shared in-memory
// session or the global ~/.pi/sessions. This does not mark responses verified.
function courseSessionLocation(course) {
  if (!course || course === '.' || course === '..' ||
      course.includes('/') || course.includes('\\') ||
        course === '.' || course === '..' || course.includes(String.fromCharCode(0)) ||
      course.includes('\0') || course !== course.trim() || course.startsWith('.')) {
    throw new Error('Invalid course name');
  }
  const data = join(cwd, 'DATA');
  if (!existsSync(data) || lstatSync(data).isSymbolicLink()) throw new Error('Invalid DATA root');
  const courseDir = join(data, course);
  if (!existsSync(courseDir) || lstatSync(courseDir).isSymbolicLink() ||
      !lstatSync(courseDir).isDirectory()) {
    throw new Error('Course does not exist or is symlinked');
  }
  const canonical = realpathSync(courseDir);
  if (canonical !== resolve(courseDir)) throw new Error('Unsafe course path');
  const runtime = join(courseDir, 'runtime');
  if (existsSync(runtime) && lstatSync(runtime).isSymbolicLink()) {
    throw new Error('Symlinked course runtime is forbidden');
  }
  mkdirSync(runtime, { recursive: true, mode: 0o700 });
  return { courseDir };
}

function authorized(request) {
  const actual = Buffer.from(request.headers.authorization || '');
  const expected = Buffer.from('Bearer ' + token);
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

function respond(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(data));
}

async function runNativeTurn(course, prompt) {
  const { courseDir } = courseSessionLocation(course);
  // One native Pi session per checked request. Discard unverified SDK history.
  const { session } = await createAgentSession({
    cwd: courseDir,
    sessionManager: SessionManager.inMemory(courseDir),
    noTools: 'all',
  });
  activeSessions.add(session);
  const timeout = setTimeout(() => { void session.abort(); }, 90_000);
  try {
    await session.prompt(prompt);
    const text = session.getLastAssistantText();
    if (typeof text !== 'string' || !text.trim() || text.length > 32_000) {
      throw new Error('Empty or excessive Pi reply');
    }
    return text;
  } finally {
    clearTimeout(timeout);
    activeSessions.delete(session);
    await session.dispose();
  }
}

const server = createServer(async (req, res) => {
  if (!authorized(req)) return respond(res, 401, { error: 'Unauthorized' });
  if (req.method === 'GET' && req.url === '/internal/health') return respond(res, 200, { gateway: 'pi', ready: true, model_verified: false });
  if (req.method !== 'POST' || req.url !== '/internal/reply') {
    return respond(res, 404, { error: 'Not found' });
  }
  try {
    let content = '';
    for await (const chunk of req) {
      content += chunk;
      if (Buffer.byteLength(content) > maxBytes) return respond(res, 413, { error: 'Too large' });
    }
    const data = JSON.parse(content);
    if (!data || typeof data !== 'object' || Array.isArray(data)) return respond(res, 400, { error: 'Invalid request' });
    const course = data.course;
    const prompt = data.prompt;
    if (typeof course !== 'string' || !course || course.length > 120 ||
        course.includes('/') || course.includes('\\') ||
        typeof prompt !== 'string' || !prompt.trim() || prompt.length > 16000) {
      return respond(res, 400, { error: 'Invalid input' });
    }
    if (busy.has(course)) return respond(res, 409, { error: 'Course is busy' });
    if (busy.size >= maxConcurrent) return respond(res, 503, { error: 'Pi gateway at capacity' });
    busy.add(course);
    try {
      const text = await runNativeTurn(course, prompt);
      if (typeof text !== 'string' || !text.trim()) {
        return respond(res, 502, { error: 'Pi did not return a message' });
      }
      return respond(res, 200, { text });
    } finally {
      busy.delete(course);
    }
  } catch (error) {
    console.error('Pi turn failed:', error instanceof Error ? error.name : 'unknown');
    return respond(res, 503, { error: 'Pi session unavailable' });
  }
});

server.listen(8787, '127.0.0.1', () => console.log('Pi SDK gateway on 127.0.0.1:8787'));
for (const signal of ['SIGTERM', 'SIGINT']) {
  process.once(signal, async () => {
    server.close();
    await Promise.all([...activeSessions].map(async session => { await session.abort(); await session.dispose(); }));
  });
}
