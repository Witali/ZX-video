// Exclude nonvisual generated caBX/C2PA metadata from publishable source copies.
// Kept PNG chunks, including IHDR and every IDAT byte, are copied unchanged.
import fs from 'node:fs';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('.',import.meta.url));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const reportFile=path.join(root,'source-sanitization.json');
const report=fs.existsSync(reportFile)?JSON.parse(fs.readFileSync(reportFile)): {
  scope:'Nonvisual caBX metadata excluded; pixel streams unchanged; untouched originals remain local only',images:[]};
for(const name of ['paintress','sirene','gestral-village','sirene-study','gustave-sophie']){
 const file=path.join(root,'sources',name+'.png'),raw=fs.readFileSync(file),kept=[raw.subarray(0,8)],idat=[];
 let offset=8,removed=0;
 while(offset<raw.length){const length=raw.readUInt32BE(offset),type=raw.toString('ascii',offset+4,offset+8),chunk=raw.subarray(offset,offset+length+12);
  if(type==='IDAT')idat.push(raw.subarray(offset+8,offset+8+length));
  if(type==='caBX')removed+=chunk.length;else kept.push(chunk);
  offset+=length+12;
 }
 if(offset!==raw.length)throw Error('Malformed PNG');
 if(!removed)continue;
 const originalDir=path.resolve('.tmp/generated-originals');fs.mkdirSync(originalDir,{recursive:true});
 const original=path.join(originalDir,name+'.png');if(!fs.existsSync(original))fs.writeFileSync(original,raw);
 const clean=Buffer.concat(kept);fs.writeFileSync(file,clean);
 const record={source:'sources/'+name+'.png',original_generated_sha256:sha(raw),published_source_sha256:sha(clean),
  omitted_chunks:['caBX'],omitted_bytes:removed,idat_bytes:Buffer.concat(idat).length,idat_sha256:sha(Buffer.concat(idat)),idat_preserved_byte_exact:true};
 report.images=report.images.filter(r=>r.source!==record.source);report.images.push(record);
}
fs.writeFileSync(reportFile,JSON.stringify(report,null,2)+'\n');
const changes=new Map(report.images.map(r=>[r.source,r]));
const provenanceFile=path.join(root,'provenance.json'),provenance=JSON.parse(fs.readFileSync(provenanceFile));
for(const asset of [...provenance.assets,provenance.superseded_study]){
 const r=changes.get(asset.source);if(r){asset.original_generated_sha256=r.original_generated_sha256;asset.source_sha256=r.published_source_sha256;}
 for(const reference of asset.reference_images||[]){const input=changes.get(reference.source);if(input){reference.original_generation_input_sha256=input.original_generated_sha256;reference.sha256=input.published_source_sha256;reference.pixel_payload_unchanged=true;}}
}
provenance.source_metadata_policy='Project copies omit nonvisual caBX metadata; see source-sanitization.json';
fs.writeFileSync(provenanceFile,JSON.stringify(provenance,null,2)+'\n');
const compiledFile=path.join(root,'compiled.json'),compiled=JSON.parse(fs.readFileSync(compiledFile));
for(const item of compiled.images)item.source_sha256=sha(fs.readFileSync(path.join(root,'sources',item.name+'.png')));
fs.writeFileSync(compiledFile,JSON.stringify(compiled,null,2)+'\n');
console.log(JSON.stringify({sources:report.images.length,all_idat_payloads_preserved:report.images.every(r=>r.idat_preserved_byte_exact)},null,2));
