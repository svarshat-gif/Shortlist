import {chromium,expect} from '@playwright/test';
import fs from 'node:fs';

const samples=['Ananya_Rao.pdf','Kabir_Siddiqui.docx','Meera_Nair.pdf'].map(name=>({name,data:fs.readFileSync('samples/'+name).toString('base64')}));
const browser=await chromium.launch({channel:'chrome',headless:true});
const context=await browser.newContext({baseURL:'http://127.0.0.1:8000',viewport:{width:1366,height:900},reducedMotion:'reduce'});
await context.addInitScript(fixtures=>{
 window.testFolder={permission:'granted',request:'granted',fixtures,rows:[fixtures[0]],options:null};
 window.showDirectoryPicker=async options=>{
  window.testFolder.options=options;
  return {kind:'directory',name:'Incoming CVs',queryPermission:async()=>window.testFolder.permission,requestPermission:async()=>window.testFolder.request,
   values:async function*(){for(const row of window.testFolder.rows)yield {kind:'file',name:row.name,getFile:async()=>new File([Uint8Array.from(atob(row.data),c=>c.charCodeAt(0))],row.name,{lastModified:1000})};}};
 };
},samples);
const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
let intakes=0;page.on('request',r=>{if(r.url().endsWith('/api/assistant/intake'))intakes++;});
async function state(){return (await context.request.get('/api/state')).json();}
async function next(){await page.getByRole('dialog').getByRole('button',{name:'Continue',exact:true}).click();}
try{
 await page.goto('/');await page.locator('.login-form button[type=submit]').click();await page.getByRole('button',{name:'Turn on the assistant',exact:true}).click();
 await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);expect((await state()).assistant.enabled).toBeFalsy();
 await page.getByRole('button',{name:'Hiring assistant',exact:true}).click();await page.getByRole('switch',{name:'Review incoming CVs'}).click();await next();await page.getByRole('dialog').getByRole('button',{name:'Use a sample job',exact:true}).click();await next();
 const dialog=page.getByRole('dialog');await dialog.getByRole('button',{name:'Choose a folder on my computer',exact:true}).click();await expect(dialog.getByText('1 CV found',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>window.testFolder.options)).toEqual({id:'shortlist-cvs',mode:'read',startIn:'documents'});
 expect((await state()).candidates).toHaveLength(0);expect((await state()).assistant.enabled).toBeFalsy();expect(intakes).toBe(0);
 await next();await dialog.getByRole('button',{name:'Back',exact:true}).click();await expect(dialog.getByText('1 CV found',{exact:true})).toBeVisible();await next();await dialog.getByRole('button',{name:'Start reviewing',exact:true}).click();
 await expect.poll(async()=>(await state()).candidates.length,{timeout:15000}).toBe(1);
 await expect.poll(async()=>Object.keys((await state()).assistant.suggestions).length,{timeout:15000}).toBe(1);
 await page.evaluate(()=>window.testFolder.rows.push(window.testFolder.fixtures[1]));
 await expect.poll(async()=>(await state()).candidates.length,{timeout:15000}).toBe(2);
 await page.evaluate(()=>window.testFolder.rows.push({...window.testFolder.fixtures[0],name:'Copy.pdf'}));
 await expect.poll(async()=>(await state()).assistant.totals.duplicates,{timeout:15000}).toBe(1);
 expect((await state()).candidates).toHaveLength(2);
 await page.getByRole('button',{name:'Assistant on',exact:true}).click();await expect(dialog.getByText('3 CVs in this folder',{exact:true})).toBeVisible();await page.screenshot({path:'test-results/browser-folder-watching.png'});
 await page.evaluate(()=>{window.testFolder.permission='denied';window.testFolder.request='denied';});
 await expect.poll(async()=>(await state()).assistant.enabled,{timeout:10000}).toBeFalsy();expect((await state()).assistant.access_granted).toBeFalsy();
 const count=intakes;await page.evaluate(()=>window.testFolder.rows.push(window.testFolder.fixtures[2]));await page.waitForTimeout(2500);expect(intakes).toBe(count);expect((await state()).candidates).toHaveLength(2);
 await dialog.getByRole('button',{name:'Set up the assistant',exact:true}).click();await next();await next();await dialog.getByRole('button',{name:'Choose a folder on my computer',exact:true}).click();await expect(dialog.getByRole('alert')).toContainText('Read access was not allowed');await expect(dialog.getByRole('button',{name:'Continue',exact:true})).toBeDisabled();
 await page.evaluate(()=>{window.testFolder.permission='granted';window.testFolder.request='granted';});await dialog.getByRole('button',{name:'Choose a folder on my computer',exact:true}).click();await expect(dialog.getByRole('alert')).toHaveCount(0);await next();await dialog.getByRole('button',{name:'Start reviewing',exact:true}).click();
 await expect.poll(async()=>(await state()).candidates.length,{timeout:15000}).toBe(3);
 expect((await state()).candidates.every(c=>!c.selected)).toBeTruthy();expect(errors).toEqual([]);
 console.log('Browser folder consent, explicit start, new arrivals, duplicates, permission loss and reconnect passed.');
}finally{await context.request.post('/api/logout');await browser.close();}
