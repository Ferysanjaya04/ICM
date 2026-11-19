"use strict";
document.addEventListener('DOMContentLoaded',async()=>{
 const error=document.getElementById('dashboard-data-error');
 try{const user=await ICMApi.getMe();document.getElementById('nav-user').textContent=user.username||'Akun';document.getElementById('app-loading').hidden=true;document.getElementById('dashboard-app').hidden=false;}
 catch(e){if(ICMApi.handleSessionError(e))return;document.getElementById('app-loading').textContent=e.message+' Muat ulang halaman untuk mencoba lagi.';return;}
 const [matches,careers]=await Promise.allSettled([ICMApi.listJobMatches(),ICMApi.listCareerRecommendations()]);
 function list(v){return Array.isArray(v)?v:Array.isArray(v?.results)?v.results:Array.isArray(v?.recommendations)?v.recommendations:[];}
 const m=matches.status==='fulfilled'?list(matches.value):[],c=careers.status==='fulfilled'?list(careers.value):[];
 if(matches.status==='rejected'||careers.status==='rejected'){for(const x of [matches,careers])if(x.status==='rejected'&&ICMApi.handleSessionError(x.reason))return;error.hidden=false;error.textContent='Sebagian riwayat belum dapat dimuat. Muat ulang untuk mencoba lagi.';}
 const both=matches.status==='fulfilled'&&careers.status==='fulfilled';document.getElementById('total-analyses').textContent=both?m.length+c.length:'—';
 if([matches,careers].some(x=>x.status==='fulfilled'&&(x.value?.next||Number(x.value?.count)>list(x.value).length)))document.getElementById('total-label').textContent='Riwayat yang dimuat';
 const score=x=>{const v=x.compatibility?.score??x.compatibility??x.compatibility_score;if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)&&n>=0&&n<=100?n:null;};
 const scores=m.map(score).filter(x=>x!==null);document.getElementById('average-score').textContent=scores.length?(scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1)+'%':'Belum tersedia';
 const date=x=>Date.parse(x.created_at)||0;const latest=[...c].filter(x=>date(x)).sort((a,b)=>date(b)-date(a))[0];
 const role=latest?.top_roles?.find(x=>Number(x.rank)===1)?.role_title??latest?.dominant_category;document.getElementById('latest-role').textContent=role||'Belum tersedia';
 const insights=document.getElementById('quick-insights');insights.replaceChildren();
 const facts=[];if(scores.length)facts.push(`Rata-rata ${scores.length} skor Job Matching yang tersedia: ${(scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1)}%.`);if(role)facts.push(`Peran pada rekomendasi karier terbaru: ${role}.`);if(both&&!m.length&&!c.length)facts.push('Belum ada insight. Jalankan analisis pertama untuk melihat ringkasannya.');if(!facts.length)facts.push('Data yang tersedia belum cukup untuk merangkum insight.');for(const text of facts){const li=document.createElement('li');li.textContent=text;insights.append(li);}
 const target=document.getElementById('recent-analyses');target.replaceChildren();const rows=[...m.map(x=>({x,type:'Job Matching',result:score(x)===null?'Skor belum tersedia':score(x).toFixed(2)+'% kecocokan'})),...c.map(x=>({x,type:'Career Recommendation',result:x.dominant_category||'Kategori belum tersedia'}))].sort((a,b)=>date(b.x)-date(a.x)).slice(0,4);
 if(!rows.length){const p=document.createElement('p');p.className='empty-state';p.textContent=both?'Belum ada analisis. Mulai dari CV dan tujuan kariermu.':'Riwayat belum tersedia saat ini.';target.append(p);}
 for(const row of rows){const a=document.createElement('a');a.href=row.x.id?'./history.html?type='+(row.type==='Job Matching'?'match':'career')+'&id='+encodeURIComponent(row.x.id):'./history.html';a.className='recent-row';const label=document.createElement('strong'),meta=document.createElement('span'),result=document.createElement('span');label.textContent=row.type;meta.textContent=date(row.x)?new Date(row.x.created_at).toLocaleDateString('id-ID',{dateStyle:'medium'}):'Tanggal tidak tersedia';result.textContent=row.result;a.append(label,meta,result);target.append(a);}
});
