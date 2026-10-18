import {useEffect,useRef,useState} from 'react';

export function useFolderIntake({state,call,onState,active}){
  const handle=useRef(null),seen=useRef(new Set()),observed=useRef(new Map()),callbacks=useRef({state,call,onState});
  callbacks.current={state,call,onState};
  const [error,setError]=useState('');
  async function list(directory){
    const files=[];
    for await(const entry of directory.values()){
      if(entry.kind==='file'&&/\.(pdf|docx)$/i.test(entry.name))files.push(await entry.getFile());
      if(files.length>=500)break;
    }
    return files.sort((a,b)=>a.name.localeCompare(b.name));
  }
  async function choose(){
    setError('');
    if(!window.showDirectoryPicker){setError('Choose a folder in Chrome or Edge, or create an app folder below.');return false;}
    try{
      const selected=await window.showDirectoryPicker({id:'shortlist-cvs',mode:'read',startIn:'documents'});
      let permission=await selected.queryPermission({mode:'read'});
      if(permission!=='granted')permission=await selected.requestPermission({mode:'read'});
      if(permission!=='granted'){setError('Read access was not allowed. Choose the folder again and allow access.');return false;}
      const files=await list(selected);
      const data=await call('/assistant/folder/connect',{name:selected.name,count:files.length,files:files.slice(0,8).map(f=>f.name),allowed:true});
      handle.current=selected;seen.current=new Set();observed.current=new Map(files.map(f=>[f.name,f.size+':'+f.lastModified]));
      onState(data);return true;
    }catch(e){if(e.name!=='AbortError')setError('The folder could not be connected. Choose it again and allow read access, or create an app folder.');return false;}
  }
  async function refresh(){
    if(callbacks.current.state.assistant?.source!=='browser')return callbacks.current.call('/assistant/folder').then(callbacks.current.onState);
    if(!handle.current){setError('Choose your CV folder again to reconnect it.');return;}
    try{
      const files=await list(handle.current);
      const data=await call('/assistant/folder/status',{count:files.length,files:files.slice(0,8).map(f=>f.name)});
      onState(data);setError('');
    }catch{setError('Folder access has ended. Choose your folder again to reconnect it.');}
  }
  function forget(){handle.current=null;seen.current=new Set();observed.current=new Map();setError('');}
  useEffect(()=>{seen.current=new Set();},[state.assistant?.retry_revision]);
  useEffect(()=>{if(!active)forget();},[active]);
  useEffect(()=>{
    if(!active||!state.assistant?.enabled||state.assistant?.source!=='browser'||!state.assistant?.access_granted)return;
    let stopped=false,busy=false,lastMetadata='';
    async function scan(){
      if(busy||stopped)return;busy=true;
      try{
        if(!handle.current)throw new Error('Reconnect');
        if(await handle.current.queryPermission({mode:'read'})!=='granted')throw new Error('Permission ended');
        const files=await list(handle.current);
        if(stopped)return;
        const metadata=JSON.stringify(files.map(f=>[f.name,f.size,f.lastModified]));
        if(metadata!==lastMetadata){
          const data=await call('/assistant/folder/status',{count:files.length,files:files.slice(0,8).map(f=>f.name)});
          if(stopped)return;callbacks.current.onState(data);lastMetadata=metadata;
        }
        const queue=[];
        for(const file of files){const version=file.size+':'+file.lastModified;const key=file.name+':'+version;const previous=observed.current.get(file.name);observed.current.set(file.name,version);if(previous===version&&!seen.current.has(key))queue.push({file,key});if(queue.length===10)break;}
        if(queue.length&&callbacks.current.state.candidates.length<50){
          const body=new FormData();queue.forEach(item=>body.append('files',item.file));
          const data=await call('/assistant/intake',body);
          if(stopped)return;
          queue.forEach(item=>seen.current.add(item.key));callbacks.current.onState(data);
        }
        setError('');
      }catch{
        if(!stopped){
          setError('The folder could not be read. Reconnect it to continue.');
          try{const data=await call('/assistant/folder/disconnect',{});if(!stopped)callbacks.current.onState(data);}catch{}
        }
      }finally{busy=false;}
    }
    scan();const timer=setInterval(scan,2000);
    return()=>{stopped=true;clearInterval(timer);};
  },[active,state.assistant?.enabled,state.assistant?.source,state.assistant?.access_granted,state.assistant?.retry_revision]);
  return {choose,refresh,forget,error};
}
