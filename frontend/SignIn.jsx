import React,{useEffect,useRef,useState} from 'react';
import './signin.css';

function Block({className=''}){
 return <div className={'scene-block '+className}>{['front','back','left','right','top','bottom'].map(face=><span key={face} className={'block-face face-'+face}/>)}</div>;
}

export function MotionArtwork({variant=0}){
 const scene=useRef(),bounds=useRef();
 const [reduced,setReduced]=useState(()=>matchMedia('(prefers-reduced-motion: reduce)').matches),[hidden,setHidden]=useState(document.hidden);
 useEffect(()=>{
  const preference=matchMedia('(prefers-reduced-motion: reduce)');const change=()=>setReduced(preference.matches),visibility=()=>setHidden(document.hidden);
  preference.addEventListener('change',change);document.addEventListener('visibilitychange',visibility);
  return()=>{preference.removeEventListener('change',change);document.removeEventListener('visibilitychange',visibility);};
 },[]);
 function reset(){scene.current?.style.setProperty('--look-x','0deg');scene.current?.style.setProperty('--look-y','0deg');}
 useEffect(()=>{if(reduced)reset();},[reduced]);
 function move(e){
  if(reduced||e.pointerType!=='mouse')return;
  const rect=bounds.current||e.currentTarget.getBoundingClientRect();
  const x=Math.max(-1,Math.min(1,(e.clientX-rect.left)/rect.width*2-1)),y=Math.max(-1,Math.min(1,(e.clientY-rect.top)/rect.height*2-1));
  scene.current.style.setProperty('--look-x',(-y*5).toFixed(2)+'deg');scene.current.style.setProperty('--look-y',(x*8).toFixed(2)+'deg');
 }
 return <div className={'signin-scene scene-variant-'+variant+' '+(reduced||hidden?'motion-paused':'')} ref={scene} onPointerEnter={e=>{bounds.current=e.currentTarget.getBoundingClientRect();}} onPointerMove={move} onPointerLeave={reset}><div className="scene-stage" aria-hidden="true"><div className="scene-shadow"/><div className="scene-tilt"><div className="scene-float"><div className="scene-model"><div className="scene-orbit"><span/><span/></div><Block className="scene-platform"/><Block className="scene-tall"/><Block className="scene-medium"/><Block className="scene-short"/><div className="scene-dot"/></div></div></div></div></div>;
}

export default function SignIn({email,password,onEmail,onPassword,onSubmit,busy}){
 return <div className="login-layout signin-continuous"><section className="login-form"><p className="eyebrow">Your hiring workspace</p><h1>Take a seat.</h1><p>Your hiring desk is ready.</p><form onSubmit={onSubmit}><label>Email address<input required type="email" autoComplete="username" value={email} onChange={e=>onEmail(e.target.value)}/></label><label>Password<input required type="password" autoComplete="current-password" value={password} onChange={e=>onPassword(e.target.value)}/></label><button className="button" disabled={busy} type="submit">Sign in <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 12h15m-6-6 6 6-6 6" stroke="currentColor" strokeWidth="1.6"/></svg></button></form></section><section className="login-story"><p className="eyebrow">Evidence before decisions</p><h2>Good people.<br/>Clear evidence.<br/><em>Better decisions.</em></h2><p className="login-description">Your next hire, with the evidence in view.</p><MotionArtwork/></section></div>;
}
