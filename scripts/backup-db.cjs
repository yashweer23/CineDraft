'use strict';
const {spawnSync}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const ROOT=path.resolve(__dirname,'..');
function backup(output,run=spawnSync){
 const destination=path.resolve(output);fs.mkdirSync(path.dirname(destination),{recursive:true});
 const fd=fs.openSync(destination,'wx',0o600);let success=false,fdOpen=true;
 try{
  const result=run('docker',['compose','exec','-T','db','sh','-c',
   'exec pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom --no-owner --no-privileges'],
   {cwd:ROOT,stdio:['ignore',fd,'pipe'],windowsHide:true});
  if(result.error||result.status!==0)throw new Error('Database backup failed. Check Docker and the db service.');
  fs.closeSync(fd);fdOpen=false;
  const read=fs.openSync(destination,'r');const header=Buffer.alloc(5);
  try{fs.readSync(read,header,0,5,0);}finally{fs.closeSync(read);}
  if(header.toString('ascii')!=='PGDMP')throw new Error('Backup output is not a PostgreSQL custom archive.');
  success=true;return {backup:destination,bytes:fs.statSync(destination).size,format:'PostgreSQL custom archive',restore_tested:false};
 }finally{
  if(fdOpen)fs.closeSync(fd);
  if(!success)fs.unlinkSync(destination);
 }
}
if(require.main===module){
 const args=process.argv.slice(2);
 if(args.length!==2||args[0]!=='--out'){console.error('Usage: node scripts/backup-db.cjs --out backups/unique-name.dump');process.exitCode=1;}
 else{try{console.log(JSON.stringify(backup(args[1]),null,2));}catch(error){console.error(error.code==='EEXIST'?'Output exists; choose a new backup filename.':error.message);process.exitCode=1;}}
}
module.exports={backup};
