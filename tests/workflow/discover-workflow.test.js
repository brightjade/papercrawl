/**
 * Behavioural tests for the github-script body in
 * `.github/workflows/discover.yml`.
 *
 *   node tests/workflow/discover-workflow.test.js
 *
 * GitHub Actions cannot run locally, and that script carries the decision this
 * whole feature turns on: whether a human is told something turned up. It had
 * no verification at all, and the two bugs found in review -- an issue edit
 * that notifies nobody, and a blind sweep closing a real finding -- were both
 * one line of logic. So the script is extracted from the workflow file itself
 * (never a copy, which would drift) and driven the way `actions/github-script`
 * drives it: the body wrapped in an async function receiving github, context,
 * core and require, with a recording stub for the issues REST surface.
 *
 * Node only, no dependencies -- the YAML block is extracted by indentation
 * rather than by parsing YAML.
 */

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const WORKFLOW = path.join(__dirname, '..', '..', '.github', 'workflows', 'discover.yml');

/** Pull the `script: |` literal block out of the workflow, dedented. */
function extractScript(yamlPath) {
  const lines = fs.readFileSync(yamlPath, 'utf8').split('\n');
  const start = lines.findIndex((l) => /^\s*script:\s*\|\s*$/.test(l));
  assert.notStrictEqual(start, -1, `no "script: |" block in ${yamlPath}`);

  const openIndent = lines[start].match(/^\s*/)[0].length;
  const body = [];
  for (const line of lines.slice(start + 1)) {
    if (line.trim() === '') {
      body.push('');
      continue;
    }
    if (line.match(/^\s*/)[0].length <= openIndent) break;
    body.push(line);
  }
  const strip = Math.min(
    ...body.filter((l) => l.trim()).map((l) => l.match(/^\s*/)[0].length)
  );
  return body.map((l) => l.slice(strip)).join('\n');
}

const SRC = extractScript(WORKFLOW);
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/**
 * The `needs-manual` rows the real registry yields on *every* sweep. These
 * venues will always need a hand-written scraper, so this set is a standing
 * state and never news -- the reason the trigger ignores it.
 */
const MANUAL = [
  ['acl', 2026], ['acl', 2027], ['emnlp', 2026], ['emnlp', 2027],
  ['naacl', 2026], ['naacl', 2027], ['eacl', 2025], ['eacl', 2026],
  ['eacl', 2027], ['coling', 2026], ['coling', 2027], ['aaai', 2027],
].map(([prefix, year]) => ({
  conf_id: `${prefix}_${year}`, prefix, year, status: 'needs-manual', count: 0,
  url: `https://${year}.${prefix}.org/`,
  note: 'registration needs a hand-written scraper',
}));

const NOT_YET = ['cvpr_2027', 'icse_2027'].map((conf_id) => ({
  conf_id, prefix: conf_id.split('_')[0], year: 2027, status: 'not-yet',
  count: 0, url: `https://example.test/${conf_id}`, note: '',
}));

const LIVE = {
  conf_id: 'usenix_security_2026', prefix: 'usenix_security', year: 2026,
  status: 'live', count: 381, url: 'https://usenix.test/sec26', note: '',
};

const EMPTY = {
  conf_id: 'cvpr_2026', prefix: 'cvpr', year: 2026, status: 'empty',
  count: 0, url: 'https://cvf.test/CVPR2026', note: '',
};

/** What every OpenReview venue reports until the repository secrets exist. */
const NO_CREDENTIALS = ['iclr_2027', 'neurips_2027', 'icml_2027', 'colm_2026', 'corl_2026'].map(
  (conf_id) => ({
    conf_id, prefix: conf_id.split('_')[0], year: 2027, status: 'unreachable',
    count: 0, url: `https://openreview.net/group?id=${conf_id}`,
    note: 'no OpenReview credentials -- venue not probed',
  })
);

const THROTTLED = {
  conf_id: 'icse_2026', prefix: 'icse', year: 2026, status: 'unreachable',
  count: 0, url: 'https://dblp.org/db/conf/icse/icse2026.html',
  note: 'HTTP 429 after 5 attempts',
};

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

function makeGithub(openIssues) {
  const calls = [];
  const record = (name) => async (args) => {
    calls.push({ name, args });
    return { data: { number: 99 } };
  };
  return {
    calls,
    api: {
      rest: {
        issues: {
          listForRepo: async (args) => {
            calls.push({ name: 'listForRepo', args });
            return { data: openIssues };
          },
          create: record('create'),
          update: record('update'),
          createComment: record('createComment'),
        },
      },
    },
  };
}

/** Run the workflow script against one sweep result, in a scratch directory. */
async function run({ results, stale = [], openIssues = [] }) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'discover-wf-'));
  const cwd = process.cwd();
  const logs = [];
  const gh = makeGithub(openIssues);
  try {
    process.chdir(dir);
    fs.writeFileSync(
      'results.json',
      JSON.stringify({
        results,
        live_count: results.filter((r) => r.status === 'live').length,
        stale_empty: stale,
      })
    );
    await new AsyncFunction('github', 'context', 'core', 'require', SRC)(
      gh.api,
      { repo: { owner: 'o', repo: 'r' } },
      { info: (m) => logs.push(m) },
      require
    );
  } finally {
    process.chdir(cwd);
    fs.rmSync(dir, { recursive: true, force: true });
  }

  const find = (name, pred = () => true) => gh.calls.find((c) => c.name === name && pred(c.args));
  return {
    calls: gh.calls.map((c) => c.name),
    logs,
    created: find('create'),
    updated: find('update', (a) => Boolean(a.title)),
    closed: find('update', (a) => a.state === 'closed'),
    comment: find('createComment'),
  };
}

// ---------------------------------------------------------------------------
// Cases
// ---------------------------------------------------------------------------

const CASES = [
  {
    name: 'the 12 standing needs-manual rows alone never open an issue',
    why: 'needs-manual is a state, not news; triggering on it made run 1 open an ' +
         'issue and every later run silently edit it, which notifies nobody',
    input: { results: [...MANUAL, ...NOT_YET] },
    check(r) {
      assert.deepStrictEqual(r.calls, ['listForRepo'], 'nothing should be written');
    },
  },
  {
    name: 'a live venue opens an issue',
    input: { results: [...MANUAL, ...NOT_YET, LIVE] },
    check(r) {
      assert.ok(r.created, 'an issue should be created');
      assert.match(r.created.args.title, /usenix_security_2026 \(381\)/);
      assert.ok(
        r.created.args.body.includes('Need a hand-written scraper'),
        'needs-manual should still ride along in the body'
      );
    },
  },
  {
    name: 'a live venue found while an issue is already open still notifies',
    why: 'GitHub sends no notification for a title or body edit, so a venue going ' +
         'live in month 5 would be silent text on an issue already dismissed',
    input: { results: [...MANUAL, ...NOT_YET, LIVE], openIssues: [{ number: 7 }] },
    check(r) {
      assert.ok(r.updated, 'the open issue should be updated');
      assert.ok(r.comment, 'a comment must fire, since an edit notifies nobody');
      assert.ok(!r.created, 'no duplicate issue');
    },
  },
  {
    name: 'a stale-empty selector alone opens an issue',
    input: { results: [...MANUAL, ...NOT_YET, EMPTY], stale: ['cvpr_2026'] },
    check(r) {
      assert.ok(r.created);
      assert.match(r.created.args.title, /Possible broken selectors: cvpr_2026/);
    },
  },
  {
    name: 'a clean sweep that finds nothing closes the open issue',
    input: { results: [...MANUAL, ...NOT_YET], openIssues: [{ number: 7 }] },
    check(r) {
      assert.ok(r.closed, 'the stale issue should be closed');
      assert.strictEqual(r.closed.args.issue_number, 7);
      assert.strictEqual(r.closed.args.state_reason, 'completed');
    },
  },
  {
    name: 'a sweep with unprobed venues leaves an open issue open',
    why: 'a sweep that learned nothing is not a sweep that found nothing -- every ' +
         'OpenReview venue is unreachable until the repository secrets are added, ' +
         'so closing on that evidence would retire a real finding from last month',
    input: {
      results: [...MANUAL, ...NOT_YET, ...NO_CREDENTIALS],
      openIssues: [{ number: 7 }],
    },
    check(r) {
      assert.ok(!r.closed, 'a blind sweep must not close anything');
      assert.ok(r.comment, 'it should say why it is leaving the issue open');
      assert.match(r.comment.args.body, /could not be probed/);
      assert.match(r.comment.args.body, /OPENREVIEW_USERNAME/);
      assert.ok(!r.created, 'and must not open a new one either');
    },
  },
  {
    name: 'a single throttled DBLP venue is enough to hold the issue open',
    why: 'unreachable is one status whatever caused it; throttling is the case it ' +
         'was introduced for',
    input: {
      results: [...MANUAL, ...NOT_YET, THROTTLED],
      openIssues: [{ number: 7 }],
    },
    check(r) {
      assert.ok(!r.closed);
      assert.match(r.comment.args.body, /HTTP 429/);
    },
  },
  {
    name: 'an inconclusive sweep with no open issue writes nothing',
    input: { results: [...MANUAL, ...NOT_YET, ...NO_CREDENTIALS] },
    check(r) {
      assert.deepStrictEqual(r.calls, ['listForRepo']);
    },
  },
  {
    name: 'unreachable venues never suppress a real finding',
    why: 'the guard is about closing, not about reporting -- a live venue is news ' +
         'even from a partly blind sweep',
    input: { results: [...MANUAL, ...NO_CREDENTIALS, LIVE] },
    check(r) {
      assert.ok(r.created, 'a live venue must still open an issue');
      assert.ok(
        r.created.args.body.includes('Not probed'),
        'the unprobed venues should be listed for context'
      );
    },
  },
];

(async () => {
  let failed = 0;
  for (const c of CASES) {
    try {
      c.check(await run(c.input));
      console.log(`  PASS  ${c.name}`);
    } catch (err) {
      failed += 1;
      console.log(`  FAIL  ${c.name}`);
      if (c.why) console.log(`        why it matters: ${c.why}`);
      console.log(`        ${err.message}`);
    }
  }
  console.log(`\n${CASES.length - failed}/${CASES.length} workflow cases passed.`);
  process.exit(failed ? 1 : 0);
})();
