import {chromium,expect} from '@playwright/test';
const browser=await chromium.launch({channel:'chrome',headless:true});
const context=await browser.newContext({baseURL:'http://127.0.0.1:8000',viewport:{width:1366,height:768},reducedMotion:'reduce'});
// The finished demo must work without reaching any external website, including fonts.
await context.route('**/*',route=>route.request().url().startsWith('http://127.0.0.1:8000')?route.continue():route.abort());
const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
async function ready(){await expect(page.locator('.working')).toHaveCount(0);}
try{
 await page.goto('/');await page.locator('.login-form input[type=password]').fill('wrong');await page.locator('.login-form button[type=submit]').click();await expect(page.getByRole('alert')).toContainText('Those details did not match');await page.locator('.login-form input[type=password]').fill('demo123');await page.locator('.login-form button[type=submit]').click();await page.getByRole('button',{name:'Continue manually',exact:true}).click();
 await page.getByRole('button',{name:'Choose a file',exact:true}).focus();await page.keyboard.press('Tab');await expect(page.locator('#job-text')).toBeFocused();
 await page.getByLabel('Choose a job file').setInputFiles('samples/Sample_Job.docx');await ready();await expect(page.getByRole('heading',{name:'Data Analyst',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Use “analyst”',exact:false}).click();await ready();await expect(page.locator('.health')).not.toContainText('Rockstar');
 await page.getByRole('button',{name:'Add ₹16–22 lakh per year',exact:false}).click();await ready();await expect(page.locator('.job-facts')).toContainText('16 to 22 lakh');
 const must=page.locator('.editable-chips').first();await must.getByRole('textbox').fill('Statistics');await must.getByRole('button',{name:'Add',exact:true}).click();await ready();await expect(must.locator('.chips')).toContainText('Statistics');await must.getByRole('button',{name:'Remove Statistics',exact:true}).click();await ready();await expect(must.locator('.chips')).not.toContainText('Statistics');
 await page.getByRole('button',{name:'Continue to CVs',exact:true}).click();await page.getByLabel('Choose CV files').setInputFiles(['samples/Ananya_Rao.pdf','samples/Kabir_Siddiqui.docx']);await ready();await expect(page.getByText('2 of 2 CVs read',{exact:true})).toBeVisible();
 await page.getByLabel('Choose CV files').setInputFiles({name:'unreadable.pdf',mimeType:'application/pdf',buffer:Buffer.from('a broken file')});await ready();await expect(page.getByText('2 of 3 CVs read',{exact:true})).toBeVisible();await expect(page.locator('.file-list')).toContainText('Save a fresh PDF or Word copy');
 await page.getByRole('button',{name:'See the ranked shortlist',exact:true}).click();await expect(page.locator('.candidate-row')).toHaveCount(2);
 await page.getByRole('button',{name:'End session',exact:true}).click();await expect(page.locator('.login-form')).toBeVisible();expect(errors).toEqual([]);
 console.log('File inputs, failures, job fixes, editable chips, keyboard navigation and offline fonts passed.');
}finally{await browser.close();}
