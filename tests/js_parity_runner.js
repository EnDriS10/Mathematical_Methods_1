// Lee un JSON con casos {id, text, vars, consts, defs, points, expected} y compara con el motor de la web.
const E = require('../docs/js/engine.js');
const cases = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
let bad = 0, total = 0;
for (const c of cases) {
  const f = E.compile(c.text, c.vars, c.constNames, c.defs);
  c.points.forEach((pt, i) => {
    const got = f(...pt, c.K), exp = c.expected[i];
    total++;
    const ok = (exp === null && !Number.isFinite(got)) || (exp !== null && Math.abs(got - exp) <= 1e-9 * (1 + Math.abs(exp)));
    if (!ok && bad++ < 12) console.log('DIFIERE', c.id, c.text, pt, 'js=', got, 'py=', exp);
  });
}
console.log(JSON.stringify({ total, bad }));
process.exit(bad ? 1 : 0);
