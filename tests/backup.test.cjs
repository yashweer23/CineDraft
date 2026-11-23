const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const os=require('node:os');const path=require('node:path');
const {backup}=require('../scripts/backup-db.cjs');
function workspace(t){const dir=fs.mkdtempSync(path.join(os.tmpdir(),'cinedraft-backup-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));return path.join(dir,'review.dump');}
test('binary backup writes directly to a file and does not claim restore success',t=>{
 const file=workspace(t);const bytes=Buffer.from([80,71,68,77,80,0,255,128,13,10]);
 const result=backup(file,(program,args,options)=>{assert.equal(program,'docker');assert.deepEqual(args.slice(0,4),['compose','exec','-T','db']);assert.equal(options.stdio[0],'ignore');fs.writeSync(options.stdio[1],bytes);return {status:0};});
 assert.deepEqual(fs.readFileSync(file),bytes);assert.equal(result.restore_tested,false);
});
test('existing backup is never overwritten',t=>{const file=workspace(t);fs.writeFileSync(file,'previous');assert.throws(()=>backup(file,()=>assert.fail('must not spawn')),/EEXIST/);assert.equal(fs.readFileSync(file,'utf8'),'previous');});
test('failed or malformed backup removes only its newly created partial output',t=>{
 const file=workspace(t);assert.throws(()=>backup(file,()=>({status:1})),/failed/);assert.equal(fs.existsSync(file),false);
 assert.throws(()=>backup(file,(_,__,opts)=>{fs.writeSync(opts.stdio[1],'not a dump');return {status:0};}),/custom archive/);assert.equal(fs.existsSync(file),false);
});
