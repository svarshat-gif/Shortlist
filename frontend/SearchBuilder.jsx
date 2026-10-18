import React,{useEffect,useRef,useState} from 'react';
import './search-builder.css';

const SITES={linkedin:{name:'LinkedIn',where:'Paste into the search bar, then choose People.',help:'https://www.linkedin.com/help/recruiter/answer/a524335'},naukri:{name:'Naukri',where:'Paste into the keyword field in Resdex, Naukri’s recruiter CV search. A recruiter account is needed.',help:'https://recruit.naukri.com/recruit/resume-database-access-resdex'}};
const normal=value=>value.toLocaleLowerCase().replace(/[\s._-]+/g,'');
const clean=value=>value.replace(/[\x00-\x1f"“”]/g,'').trim();
const dedupe=values=>values.filter((value,index)=>values.findIndex(other=>normal(other)===normal(value))===index);

function Copy({text,label,disabled,onError}){
 const [copied,setCopied]=useState(false);useEffect(()=>setCopied(false),[text]);
 return <button className="button small" disabled={disabled} onClick={async()=>{try{await navigator.clipboard.writeText(text);setCopied(true);setTimeout(()=>setCopied(false),1800);}catch{onError('Copying was not available. Select the text and copy it with your keyboard.');}}}>{copied?'Copied':label}</button>;
}

function TermPicker({kind,selected,base,catalogue,onAdd,onToggle,onRemove,disabled}){
 const [text,setText]=useState(''),[custom,setCustom]=useState([]);
 const isRole=kind==='role',limit=isRole?8:12,term=clean(text);
 const all=dedupe([...base,...selected,...custom,...catalogue]);
 const matches=term?all.filter(value=>normal(value).includes(normal(term))):dedupe([...base,...selected,...custom]);
 const visible=matches.slice(0,12),exact=all.find(value=>normal(value)===normal(term));
 function add(){if(!term||disabled)return;const value=exact||term;onAdd(value);setCustom(current=>dedupe([...current,value]));setText('');}
 return <fieldset className="term-picker"><legend>{isRole?'Job titles':'Skills to look for'} {isRole&&<small>At least one</small>}</legend><p>{isRole?'Find a role, or add your own title.':'Find a skill, or add one you need.'}</p><label className="sr-only" htmlFor={'find-'+kind}>{isRole?'Find or add a job title':'Find or add a skill'}</label><div className="term-search"><input id={'find-'+kind} type="search" autoComplete="off" maxLength={100} value={text} disabled={disabled} placeholder={isRole?'Try React developer':'Try TypeScript'} onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();add();}if(e.key==='Escape')setText('');}}/><button type="button" className="button secondary small" disabled={disabled||!term||(selected.length>=limit&&!selected.some(v=>normal(v)===normal(term)))} onClick={add}>Add {kind}</button></div><div className="selected-search-terms" aria-label={'Selected '+(isRole?'job titles':'skills')} role="group">{selected.map(value=><span className="selected-search-term" key={value}>{value}<button type="button" aria-label={'Remove '+kind+' '+value} disabled={disabled||(isRole&&selected.length===1)} onClick={()=>onRemove(value)}>×</button></span>)}</div><div className="search-choices">{visible.map(value=>{const chosen=selected.some(term=>normal(term)===normal(value));return <button type="button" key={value} aria-pressed={chosen} disabled={disabled||(!chosen&&selected.length>=limit)||(chosen&&isRole&&selected.length===1)} onClick={()=>onToggle(value)}><span aria-hidden="true">{chosen?'✓':'+'}</span>{value}</button>;})}</div>{term&&!matches.length&&<p className="term-search-note">No suggestions found. Choose “Add {kind}” to use your own.</p>}{term&&matches.length>12&&<p className="term-search-note">Showing 12 of {matches.length} matches. Keep typing to narrow them.</p>}{selected.length>=limit&&<p className="term-search-note">{limit} {isRole?'titles':'skills'} selected. Remove one to add another.</p>}</fieldset>;
}

export default function SearchBuilder({job,search,onSearch,call,onError}){
 const [site,setSite]=useState('linkedin'),[options,setOptions]=useState(search?.settings),[updating,setUpdating]=useState(false),[error,setError]=useState('');
 const [request,setRequest]=useState(search?.request_text||''),[generating,setGenerating]=useState(false),[requestError,setRequestError]=useState(''),[catalogue,setCatalogue]=useState({titles:[],skills:[]}),[retry,setRetry]=useState(0);
 const tabs=useRef(),timer=useRef(),version=useRef(0),queue=useRef(Promise.resolve()),mounted=useRef(true),committed=useRef(JSON.stringify(search?.settings));
 const latest=useRef({onSearch,onError});latest.current={onSearch,onError};
 function enqueue(fn){const next=queue.current.catch(()=>{}).then(fn);queue.current=next;return next;}
 useEffect(()=>{mounted.current=true;let cancelled=false;call('/search/catalog').then(data=>{if(!cancelled)setCatalogue(data);}).catch(()=>{});return()=>{cancelled=true;mounted.current=false;clearTimeout(timer.current);};},[]);
 useEffect(()=>{
  if(!options||JSON.stringify(options)===committed.current)return;
  const sequence=++version.current;setUpdating(true);setError('');
  timer.current=setTimeout(()=>enqueue(()=>call('/search',options)).then(data=>{
   if(!mounted.current||sequence!==version.current)return;
   committed.current=JSON.stringify(data.settings);setOptions(data.settings);latest.current.onSearch(data);setUpdating(false);
  }).catch(e=>{if(mounted.current&&sequence===version.current){setError(e.message);setUpdating(false);}}),250);
  return()=>clearTimeout(timer.current);
 },[JSON.stringify(options),retry]);
 async function generate(reset=false){
  clearTimeout(timer.current);const sequence=++version.current;setGenerating(true);setUpdating(false);setError('');setRequestError('');
  try{
   const data=await enqueue(()=>call(reset?'/search/reset':'/search/generate',reset?{}:{text:request}));
   if(!mounted.current||sequence!==version.current)return;
   committed.current=JSON.stringify(data.settings);setOptions(data.settings);latest.current.onSearch(data);if(reset)setRequest('');
  }catch(e){if(mounted.current&&sequence===version.current)setRequestError(e.message);}
  finally{if(mounted.current&&sequence===version.current)setGenerating(false);}
 }
 if(!search||!options)return <p role="status">Preparing the search…</p>;
 function change(update){setOptions(current=>({...current,...update}));}
 function add(kind,value){setOptions(current=>{if(current[kind].some(term=>normal(term)===normal(value))||current[kind].length>=(kind==='titles'?8:12))return current;return {...current,[kind]:[...current[kind],value]};});}
 function remove(kind,value){setOptions(current=>{const next=current[kind].filter(term=>normal(term)!==normal(value));return kind==='titles'&&!next.length?current:{...current,[kind]:next};});}
 function toggle(kind,value){if(options[kind].some(term=>normal(term)===normal(value)))remove(kind,value);else add(kind,value);}
 const config=options,platform=SITES[site],smart=search[site].smart,simple=search[site].simple;
 const stale=JSON.stringify(options)!==JSON.stringify(search.settings),busy=updating||generating||stale;
 const intent='Find people with '+(config.titles.length>1?'any of these titles':'this title')+': '+config.titles.join(', ')+'. '+(config.skills.length?(config.breadth==='focused'?'Require all selected skills: ':'Look for at least one selected skill: ')+config.skills.join(', ')+'. ':'Start with titles only. ')+(config.exclude_internships?'Leave out profiles mentioning intern or internship. ':'')+(config.exclude_terms?.length?'Leave out: '+config.exclude_terms.join(', ')+'.':'');
 const link=site==='linkedin'?'https://www.linkedin.com/search/results/people/?keywords='+encodeURIComponent(smart):'https://recruit.naukri.com/recruit/resume-database-access-resdex';
 return <section className="search-builder" aria-label="Candidate search builder">
  <div className="search-tabs" role="tablist" aria-label="Job sites" ref={tabs} onKeyDown={e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const next=e.key==='Home'?'linkedin':e.key==='End'?'naukri':site==='linkedin'?'naukri':'linkedin';setSite(next);tabs.current.querySelector('[data-site="'+next+'"]').focus();}}>{Object.entries(SITES).map(([id,p])=><button role="tab" id={'tab-'+id} aria-controls="search-results" aria-selected={site===id} tabIndex={site===id?0:-1} key={id} data-site={id} onClick={()=>setSite(id)}>{p.name}</button>)}</div>
  <div className="search-explainer"><span className="section-label">Find the people you need</span><h2>Build the search you need.</h2><p>Find roles and skills below, or describe a specific request. Use the finished search on {platform.name}.</p></div>
  <form className="search-request" onSubmit={e=>{e.preventDefault();generate();}}><label htmlFor="sourcing-request">Describe who you need</label><textarea id="sourcing-request" rows={3} maxLength={2000} value={request} disabled={generating} onChange={e=>setRequest(e.target.value)} placeholder="Find a senior React developer in Pune with TypeScript and Node.js, 3 to 5 years."/><div className="search-request-actions"><button type="submit" className="button small" disabled={generating||request.trim().length<8}>{generating?'Preparing your search…':'Generate search'}</button><button type="button" className="text-button" disabled={generating} onClick={()=>generate(true)}>Use the current job</button></div>{requestError&&<p className="setup-error" role="alert">{requestError}</p>}{search.notes?.length>0&&<p className="request-notes" role="status">{'Search ready for '+config.titles.join(', ')+'. '+search.notes.join(' ')}</p>}</form>
  <div className="search-workbench"><div className="search-config">
   <TermPicker kind="role" selected={config.titles} base={dedupe(search.request_text?config.titles:[job.role,...search.titles])} catalogue={catalogue.titles} onAdd={value=>add('titles',value)} onRemove={value=>remove('titles',value)} onToggle={value=>toggle('titles',value)} disabled={generating}/>
   <TermPicker kind="skill" selected={config.skills} base={dedupe(search.request_text?config.skills:[...job.must,...job.nice])} catalogue={catalogue.skills} onAdd={value=>add('skills',value)} onRemove={value=>remove('skills',value)} onToggle={value=>toggle('skills',value)} disabled={generating}/>
   <label className="search-breadth">Search breadth<select aria-label="Search breadth" disabled={generating} value={config.breadth} onChange={e=>change({breadth:e.target.value})}><option value="focused">Match all selected skills</option><option value="wider">Match any selected skill</option></select></label>
   <label className="check-label search-exclusion"><input type="checkbox" checked={config.exclude_internships} disabled={generating} onChange={e=>change({exclude_internships:e.target.checked})}/>Leave out internship mentions</label>{config.exclude_internships&&<p className="caption">This may also hide experienced people whose profiles mention an old internship.</p>}
   {config.exclude_terms?.length>0&&<div className="request-exclusions"><span className="field-label">Leave out keywords</span><div className="selected-search-terms">{config.exclude_terms.map(value=><span className="selected-search-term" key={value}>{value}<button aria-label={'Stop excluding '+value} disabled={generating} onClick={()=>change({exclude_terms:config.exclude_terms.filter(v=>v!==value)})}>×</button></span>)}</div></div>}
   <div className="search-filter-note"><strong>Set these filters on {platform.name}</strong><label>Search location<input maxLength={100} disabled={generating} value={config.location??search.filters?.location??job.location} onChange={e=>change({location:e.target.value})}/></label><label>Search experience<input maxLength={100} disabled={generating} value={config.experience??search.filters?.experience??job.experience} onChange={e=>change({experience:e.target.value})}/></label><span>These filters belong to this search.</span></div>
  </div><div className="search-output" id="search-results" role="tabpanel" aria-labelledby={'tab-'+site} aria-busy={busy}><div className="search-intent"><span className="section-label">What this finds</span><p aria-live="polite">{intent}</p></div>{error&&<div className="search-save-error" role="alert"><p className="setup-error">{error}</p><button className="text-button" onClick={()=>setRetry(retry+1)}>Try again</button></div>}
   <section className="search-block"><p className="eyebrow">Ready to paste</p><div className="section-top"><h2>Your {platform.name} search</h2><Copy text={smart} label="Copy smart search" disabled={busy} onError={onError}/></div><pre className="search-text" tabIndex="0" aria-label={platform.name+' search text'}>{smart}</pre><span className="draft">Generated from your request. Check before use.</span>{(updating||generating)&&<p className="search-updating" role="status">Updating your search…</p>}</section>
   <div className="search-howto"><h3>Use it in three moves.</h3><ol><li><b>Copy</b> the search above.</li><li><b>Open {platform.name}.</b> {platform.where}</li><li><b>Set the filters</b> for location and experience, then review the results.</li></ol><a className="button secondary small" aria-disabled={busy||undefined} href={busy?undefined:link} target="_blank" rel="noreferrer">Open {site==='naukri'?'Naukri Resdex':'LinkedIn People'} <span aria-hidden="true">↗</span></a><a className="search-help" href={platform.help} target="_blank" rel="noreferrer">View {platform.name}’s search guidance ↗</a></div>
   <details className="search-meaning"><summary>What do AND, OR and NOT mean?</summary><p><b>AND</b> requires both skills. <b>OR</b> accepts an alternative. <b>NOT</b> leaves a term out. Quotation marks keep a phrase together. Parentheses group alternatives.</p><p>Exact matches and the number of allowed search terms can vary by account. If a search is too restrictive, choose “Match any selected skill” or try the simple version below.</p></details>
   <section className="search-block simple-block"><p className="eyebrow">A simpler starting point</p><div className="section-top"><h2>Simple keywords</h2><Copy text={simple} label="Copy simple keywords" disabled={busy} onError={onError}/></div><p>Use this when the site’s basic keyword search works better. It uses your first selected title and the selected skills.</p><pre className="search-text simple-search" tabIndex="0" aria-label="Simple search keywords">{simple}</pre></section>
  </div></div>
 </section>;
}
