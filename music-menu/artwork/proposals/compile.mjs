import fs from 'node:fs';
import zlib from 'node:zlib';
import crypto from 'node:crypto';

// Compile generated reference-led art into genuine 6912-byte Spectrum screens.
// Area integration reduces the source once; each hardware attribute cell then
// selects its least-error legal pair from that scene's restricted palette.
// No inter-cell error diffusion or FLASH is used. Footer pixels are authored
// once from Cinzel, then reused byte-for-byte with scene-specific ink colors.
const crcTable=Array.from({length:256},(_,n)=>{for(let j=0;j<8;j++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0;});
function crc(b){let c=0xffffffff;for(const n of b)c=crcTable[(c^n)&255]^(c>>>8);return(c^0xffffffff)>>>0;}
function chunk(name,data){const b=Buffer.alloc(data.length+12);b.writeUInt32BE(data.length);b.write(name,4);data.copy(b,8);b.writeUInt32BE(crc(b.subarray(4,-4)),b.length-4);return b;}
function png(width,height,rgb){const header=Buffer.alloc(13);header.writeUInt32BE(width);header.writeUInt32BE(height,4);header[8]=8;header[9]=2;const rows=Buffer.alloc((width*3+1)*height);for(let y=0;y<height;y++)Buffer.from(rgb.subarray(y*width*3,(y+1)*width*3)).copy(rows,y*(width*3+1)+1);return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',zlib.deflateSync(rows)),chunk('IEND',Buffer.alloc(0))]);}
function readPNG(b){const w=b.readUInt32BE(16),h=b.readUInt32BE(20),channels=b[25]===2?3:b[25]===6?4:0;if(b[24]!==8||!channels||b[28])throw Error('Expected non-interlaced RGB/RGBA8 PNG');let o=8,idat=[];while(o<b.length){let n=b.readUInt32BE(o);if(b.toString('ascii',o+4,o+8)==='IDAT')idat.push(b.subarray(o+8,o+8+n));o+=n+12;}const raw=zlib.inflateSync(Buffer.concat(idat)),pixels=new Uint8Array(w*h*channels),stride=w*channels;
 for(let y=0;y<h;y++){const filter=raw[y*(stride+1)];for(let x=0;x<stride;x++){const a=x>=channels?pixels[y*stride+x-channels]:0,up=y?pixels[(y-1)*stride+x]:0,c=y&&x>=channels?pixels[(y-1)*stride+x-channels]:0;let p=a+up-c,pa=Math.abs(p-a),pb=Math.abs(p-up),pc=Math.abs(p-c);const predictor=filter===0?0:filter===1?a:filter===2?up:filter===3?(a+up)>>1:filter===4?pa<=pb&&pa<=pc?a:pb<=pc?up:c:NaN;if(!Number.isFinite(predictor))throw Error('PNG filter');pixels[y*stride+x]=(raw[y*(stride+1)+x+1]+predictor)&255;}}
 return {w,h,channels,pixels};}
const palette=Array.from({length:8},(_,i)=>[(i&2)?255:0,(i&4)?255:0,(i&1)?255:0]);
const offset=(x,y)=>((y&0xc0)<<5)|((y&7)<<8)|((y&0x38)<<2)|x;
// Reuse the exact already-rasterized shared Cinzel wordmark; no font lookup.
const wordmarkBytes=fs.readFileSync(new URL('wordmark-mask.json',import.meta.url));
const wordmark=JSON.parse(wordmarkBytes);
if(wordmark.width!==256||wordmark.height!==32)throw Error('Unexpected wordmark geometry');
const mask=wordmark.rows.flatMap(row=>Array.from({length:256},(_,x)=>(parseInt(row.slice((x>>3)*2,(x>>3)*2+2),16)>>(7-(x&7)))&1));
const assets=[['paintress',.84,6],['sirene',.785,3],['gestral-village',.8,6],['gustave-sophie',.8333333333333334,2]];
const sceneColors={paintress:[0,1,6,7],sirene:[0,1,3,6,7],'gestral-village':[0,2,4,6,7],'gustave-sophie':[0,1,2,7]};
const borders={paintress:0,sirene:0,'gestral-village':6,'gustave-sophie':0};
const reports=[];
for(const [name,crop,accent]of assets){const file=new URL(`sources/${name}.png`,import.meta.url);const source=fs.readFileSync(file),src=readPNG(source),target=new Float32Array(256*192*3);for(let y=0;y<160;y++)for(let x=0;x<256;x++){const x0=x*src.w/256,x1=(x+1)*src.w/256,y0=y*src.h*crop/160,y1=(y+1)*src.h*crop/160;let total=0;for(let sy=Math.floor(y0);sy<Math.ceil(y1);sy++)for(let sx=Math.floor(x0);sx<Math.ceil(x1);sx++){let weight=(Math.min(sx+1,x1)-Math.max(sx,x0))*(Math.min(sy+1,y1)-Math.max(sy,y0));total+=weight;for(let c=0;c<3;c++)target[(y*256+x)*3+c]+=src.pixels[(sy*src.w+sx)*src.channels+c]*weight;}for(let c=0;c<3;c++)target[(y*256+x)*3+c]/=total;}
 const scr=Buffer.alloc(6912),indices=new Uint8Array(256*192);
 for(let ty=0;ty<20;ty++)for(let tx=0;tx<32;tx++){let best=Infinity,pair;const distances=[];for(let y=0;y<8;y++)for(let x=0;x<8;x++){const i=((ty*8+y)*256+tx*8+x)*3;distances.push(palette.map(p=>.25*(target[i]-p[0])**2+.6*(target[i+1]-p[1])**2+.15*(target[i+2]-p[2])**2));}
  const allowed=sceneColors[name];
  for(const a of allowed)for(const b of allowed){if(b<a)continue;let error=0;for(const ds of distances)error+=Math.min(ds[a],ds[b]);if(error<best){best=error;pair=[a,b];}}
  const [paper,ink]=pair;scr[6144+ty*32+tx]=64|(paper<<3)|ink;for(let y=0;y<8;y++){let byte=0;for(let x=0;x<8;x++){const ds=distances[y*8+x],on=ds[ink]<ds[paper];indices[(ty*8+y)*256+tx*8+x]=on?ink:paper;if(on)byte|=128>>x;}scr[offset(tx,ty*8+y)]=byte;}}
 for(let y=160;y<192;y++)for(let tx=0;tx<32;tx++){const ink=y<176?7:accent;scr[6144+(y>>3)*32+tx]=64|ink;let byte=0;for(let x=0;x<8;x++){const on=mask[(y-160)*256+tx*8+x];if(on)byte|=128>>x;indices[y*256+tx*8+x]=on?ink:0;}scr[offset(tx,y)]=byte;}
 const rgb=new Uint8Array(256*192*3);let luma=0;const counts=Array(8).fill(0);for(let i=0;i<indices.length;i++){rgb.set(palette[indices[i]],i*3);if(i<256*160){const p=palette[indices[i]];luma+=(.2126*p[0]+.7152*p[1]+.0722*p[2])/255;counts[indices[i]]++;}}luma/=256*160;const dominant=[...Array(8).keys()].sort((a,b)=>counts[b]-counts[a]);const border=luma>.43?dominant.find(c=>c===5||c===6||c===7)??7:0;
 fs.writeFileSync(new URL(`${name}.scr`,import.meta.url),scr);fs.writeFileSync(new URL(`${name}-native.png`,import.meta.url),png(256,192,rgb));const scale=3,large=new Uint8Array(768*576*3);for(let y=0;y<576;y++)for(let x=0;x<768;x++)large.set(rgb.subarray(((y/3|0)*256+(x/3|0))*3,((y/3|0)*256+(x/3|0))*3+3),(y*768+x)*3);fs.writeFileSync(new URL(`${name}-preview.png`,import.meta.url),png(768,576,large));
 reports.push({name,source_sha256:crypto.createHash('sha256').update(source).digest('hex'),scr_sha256:crypto.createHash('sha256').update(scr).digest('hex'),border:borders[name],automatic_border_candidate:border,art_luminance:luma,bytes:scr.length,flash_cells:0,colors_per_cell:2});}
fs.writeFileSync(new URL('compiled.json',import.meta.url),JSON.stringify({scope:'Four selected artwork proposals; native TRD RAM/timing integration qualified separately',wordmark:'Exact shared Cinzel 1-bit mask; no local font fallback',wordmark_mask_sha256:crypto.createHash('sha256').update(wordmarkBytes).digest('hex'),images:reports},null,2)+'\n');console.log(JSON.stringify(reports,null,2));
