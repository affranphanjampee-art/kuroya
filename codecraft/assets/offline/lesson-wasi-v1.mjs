/* Ephemeral, sandboxed WASI preview1 filesystem used ONLY for lesson examples.
   Files live in this instance's memory, never access disk or network, and are discarded after each run. */
const OK=0, EBADF=8, EEXIST=20, EINVAL=28, EISDIR=31, ENOENT=44, ENOSYS=52, ENOTDIR=54, ENOSPC=51, ESPIPE=70;
const MAX_FILE=1024*1024,MAX_TOTAL=4*1024*1024,MAX_FILES=32,MAX_FDS=64;
export class WasiExit extends Error{constructor(code){super(`exit(${code})`);this.code=code}}
export function createWasi({args,stdin,write}){
 let memory=null,stdinOffset=0,nextFd=4; const enc=new TextEncoder(),dec=new TextDecoder(); const decoders={1:new TextDecoder(),2:new TextDecoder()};
 const argBytes=args.map(x=>enc.encode(x+'\0')), files=new Map(), fds=new Map();
 const view=()=>new DataView(memory.buffer), bytes=()=>new Uint8Array(memory.buffer);
 function iovecs(ptr,count){if(count>1024)throw Error('too many iovecs');let dv=view(),r=[];for(let i=0;i<count;i++)r.push([dv.getUint32(ptr+i*8,true),dv.getUint32(ptr+i*8+4,true)]);return r}
 function copyStrings(list,ptrs,buf){let dv=view(),off=buf;list.forEach((v,i)=>{dv.setUint32(ptrs+i*4,off,true);bytes().set(v,off);off+=v.length});return OK}
 function nameAt(ptr,len){if(len>255)return null;let n=dec.decode(bytes().subarray(ptr,ptr+len));if(!n||n.includes('\0')||n.includes('\\')||n.startsWith('/')||n.split('/').some(p=>p==='..'||p===''||p==='.')||n.includes('/'))return null;return n}
 function fileStat(ptr,size){let dv=view();for(let i=0;i<64;i++)dv.setUint8(ptr+i,0);dv.setUint8(ptr+16,4);dv.setBigUint64(ptr+32,BigInt(size),true)}
 const wasi={
 args_sizes_get(a,b){view().setUint32(a,argBytes.length,true);view().setUint32(b,argBytes.reduce((s,v)=>s+v.length,0),true);return OK},args_get:(a,b)=>copyStrings(argBytes,a,b),environ_sizes_get(a,b){view().setUint32(a,0,true);view().setUint32(b,0,true);return OK},environ_get:()=>OK,
 fd_prestat_get(fd,ptr){if(fd!==3)return EBADF;let dv=view();dv.setUint8(ptr,0);dv.setUint32(ptr+4,1,true);return OK},fd_prestat_dir_name(fd,ptr,len){if(fd!==3)return EBADF;if(len<1)return EINVAL;bytes()[ptr]=46;return OK},
 path_open(fd,dirflags,pathPtr,pathLen,oflags,rights,inherit,flags,out){if(fd!==3)return EBADF;let n=nameAt(pathPtr,pathLen);if(!n)return EINVAL;if(oflags&2)return ENOTDIR;let exists=files.has(n);if(exists&&(oflags&4)&&(oflags&1))return EEXIST;if(!exists&&!(oflags&1))return ENOENT;if(!exists){if(files.size>=MAX_FILES)return ENOSPC;files.set(n,new Uint8Array())}if(oflags&8)files.set(n,new Uint8Array());if(fds.size>=MAX_FDS)return ENOSPC;let id=nextFd++;fds.set(id,{name:n,pos:(flags&1)?files.get(n).length:0,append:!!(flags&1)});view().setUint32(out,id,true);return OK},
 path_filestat_get(fd,flags,ptr,len,out){if(fd!==3)return EBADF;let n=nameAt(ptr,len);if(!n)return EINVAL;if(!files.has(n))return ENOENT;fileStat(out,files.get(n).length);return OK},
 fd_fdstat_get(fd,ptr){if(fd>3&&!fds.has(fd))return EBADF;let dv=view();for(let i=0;i<24;i++)dv.setUint8(ptr+i,0);dv.setUint8(ptr,fd===3?3:fd>3?4:2);dv.setBigUint64(ptr+8,0xffffffffffffffffn,true);dv.setBigUint64(ptr+16,0xffffffffffffffffn,true);return OK},
 fd_filestat_get(fd,ptr){if(fd>3&&fds.has(fd)){fileStat(ptr,files.get(fds.get(fd).name).length);return OK}if(fd<=3){fileStat(ptr,0);return OK}return EBADF},
 fd_write(fd,iovs,count,out){let total=0;if(fd===1||fd===2){for(let [p,n] of iovecs(iovs,count)){write(fd,decoders[fd].decode(bytes().subarray(p,p+n),{stream:true}));total+=n}view().setUint32(out,total,true);return OK}let f=fds.get(fd);if(!f)return EBADF;let old=files.get(f.name);if(f.append)f.pos=old.length;let chunks=iovecs(iovs,count);let length=chunks.reduce((s,v)=>s+v[1],0),end=f.pos+length,all=[...files.values()].reduce((s,v)=>s+v.length,0);if(end>MAX_FILE||all-old.length+Math.max(old.length,end)>MAX_TOTAL)return ENOSPC;let data=new Uint8Array(Math.max(old.length,end));data.set(old);for(let [p,n] of chunks){data.set(bytes().subarray(p,p+n),f.pos);f.pos+=n;total+=n}files.set(f.name,data);view().setUint32(out,total,true);return OK},
 fd_read(fd,iovs,count,out){let total=0,f=fds.get(fd);if(fd!==0&&!f)return EBADF;let data=fd===0?stdin:files.get(f.name);let offset=fd===0?stdinOffset:f.pos;for(let [p,n] of iovecs(iovs,count)){let chunk=data.subarray(offset,offset+n);bytes().set(chunk,p);offset+=chunk.length;total+=chunk.length;if(chunk.length<n)break}if(fd===0)stdinOffset=offset;else f.pos=offset;view().setUint32(out,total,true);return OK},
 fd_seek(fd,offset,whence,out){let f=fds.get(fd);if(!f)return fd<=2?ESPIPE:EBADF;let size=files.get(f.name).length,position=(whence===0?0:whence===1?f.pos:whence===2?size:NaN)+Number(offset);if(!Number.isSafeInteger(position)||position<0||position>MAX_FILE)return EINVAL;f.pos=position;view().setBigUint64(out,BigInt(position),true);return OK},
 fd_tell(fd,out){let f=fds.get(fd);if(!f)return EBADF;view().setBigUint64(out,BigInt(f.pos),true);return OK},fd_close(fd){if(fd<=3)return OK;return fds.delete(fd)?OK:EBADF},fd_sync(fd){return fd<=3||fds.has(fd)?OK:EBADF},fd_datasync(fd){return fd<=3||fds.has(fd)?OK:EBADF},
 clock_res_get(id,p){view().setBigUint64(p,1000n,true);return OK},clock_time_get(id,precision,p){if(id>3)return EINVAL;view().setBigUint64(p,id===0?BigInt(Date.now())*1000000n:BigInt(Math.round(performance.now()*1e6)),true);return OK},random_get(p,n){for(let i=0;i<n;i+=65536)crypto.getRandomValues(bytes().subarray(p+i,p+Math.min(n,i+65536)));return OK},sched_yield:()=>OK,proc_exit(c){throw new WasiExit(c)}
 };
 const imports={wasi_snapshot_preview1:new Proxy(wasi,{get:(t,n)=>t[n]??(()=>ENOSYS)})};
 function start(instance){memory=instance.exports.memory;try{instance.exports._start();return 0}catch(e){if(e instanceof WasiExit)return e.code;throw e}finally{for(let fd of [1,2]){let rest=decoders[fd].decode();if(rest)write(fd,rest)}}}
 return{imports,start};
}
