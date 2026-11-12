const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../portfolio/app/static/transactions.js'), 'utf8');
const start = source.indexOf('function transactionSaveFailure(error){');
const end = source.indexOf('\nfunction bindTransactions(){', start);
assert(start >= 0 && end > start, 'timeout helper should be defined at module scope');

const context = vm.createContext({ui: value => value});
vm.runInContext(source.slice(start, end), context);
const explain = error => vm.runInContext('transactionSaveFailure(error)', vm.createContext({
  ui: value => value,
  error,
  transactionSaveFailure: vm.runInContext('transactionSaveFailure', context)
}));

for (const kind of ['TimeoutError', 'AbortError']) {
  const message = explain({name: kind});
  assert.match(message, /Controleer eerst het transactieoverzicht/);
  assert.match(message, /voordat je opnieuw opslaat/);
}
assert.equal(explain({name:'Error', message:'Serverfout'}), 'Serverfout');
assert.equal(explain({name:'Error'}), 'Opslaan mislukt. Probeer opnieuw.');
console.log('Phase 9: ambiguous transaction saves show safe guidance, not blind retries.');
