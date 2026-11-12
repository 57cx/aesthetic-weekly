import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';

test('daily issues from 2026-11-13 must have 2 to 6 topics', () => {
  const code = `
import sys
sys.path.insert(0, 'tools')
from daily_rules import validate_topic_count
validate_topic_count('2026-11-13', True, 2)
validate_topic_count('2026-11-13', True, 3)
validate_topic_count('2026-11-30', True, 6)
validate_topic_count('2026-11-07', False, 4)
validate_topic_count('2026-11-07', False, 1)
for bad in (1, 7):
    try:
        validate_topic_count('2026-11-13', True, bad)
    except ValueError:
        continue
    raise SystemExit(f'should reject {bad}')
try:
    validate_topic_count('2026-12-01', True, 0)
except ValueError:
    pass
else:
    raise SystemExit('should reject 0')
print('ok')
`;
  const out = execFileSync('python3', ['-c', code], {encoding: 'utf8'});
  assert.match(out, /ok/);
});
