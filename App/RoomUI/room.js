/* Shared presentation. Browser fixtures and native controllers supply the same state contract. */
(() => {
  'use strict';
  const root = document.getElementById('companion-room'), q = s => root.querySelector(s);
  const device=q('.device'), chat=q('.chat'), input=q('textarea'), overlay=q('.overlay');
  const native=!!window.webkit?.messageHandlers?.room;
  const escape = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${window.roomIcons[name] || ''}</svg>`;
  function icons(scope=root){scope.querySelectorAll('[data-lucide]').forEach(e=>e.outerHTML=icon(e.dataset.lucide));}
  let state={messages:[],notes:[],busy:false,ready:false,draft:'',draftVersion:0,appearance:'system',capture:null,dictation:null};
  let page=null,selected=null,transcript=false,focusBefore=null,toastTimer;
  let draftVersion=0,localDraft='',lastLibrary='',lastPanel='',lastToast='',suppressedClickUntil=0;
  const transport = (action, value={}) => {
    const command={version:1,action,...value};
    if(native) window.webkit.messageHandlers.room.postMessage(command);
    else preview(command);
  };
  function panel(title,html){
    overlay.classList.remove('leaving');
    if(overlay.hidden) focusBefore=document.activeElement;
    q('.panel-head h2').textContent=title;q('.panel').setAttribute('aria-label',title);
    q('.panel-body').innerHTML=html; overlay.hidden=false;device.classList.add('covered');
    q('.shell').inert=true;q('.library').inert=true;icons();
    q('[data-act=close]').focus({preventScroll:true});
  }
  function close(){
    if(overlay.hidden)return;
    page=null;lastPanel='';transport('close-note');overlay.classList.add('leaving');device.classList.remove('covered');
    if(matchMedia('(prefers-reduced-motion:reduce)').matches)finishClose();
    else {
      // The compositor may start after this click. Do not cut its exit short with a 220ms wall-clock timer.
      const animations=q('.panel').getAnimations();
      if(animations.length)Promise.all(animations.map(a=>a.finished)).then(()=>{
        if(overlay.classList.contains('leaving'))finishClose();
      }).catch(()=>{}); // Reopening cancels the old exit intentionally.
      else finishClose();
    }
  }
  function finishClose(){
    overlay.hidden=true;overlay.classList.remove('leaving');q('.shell').inert=device.classList.contains('notes-open');
    q('.library').inert=!device.classList.contains('notes-open');
    if(focusBefore?.isConnected)focusBefore.focus({preventScroll:true});
  }
  function tab(notes,focusSearch=false){
    input.blur();device.classList.toggle('notes-open',notes);q('.library').inert=!notes;q('.shell').inert=notes;
    if(focusSearch){q('.library-scroll').scrollTop=0;q('.note-search input').focus({preventScroll:true});}
    else requestAnimationFrame(()=>q(notes?'[data-act=chat]':'[data-act=notes]').focus({preventScroll:true}));
    if(notes)transport('library');
  }
  function toast(text,persistent=false){
    clearTimeout(toastTimer);const el=q('.toast');el.classList.remove('leaving');
    el.innerHTML=`<span>${escape(text)}</span><button data-act="dismiss-toast" aria-label="Dismiss message">${icon('x')}</button>`;
    el.hidden=false;if(!persistent)toastTimer=setTimeout(dismissToast,2300);
  }
  function dismissToast(){
    clearTimeout(toastTimer);const el=q('.toast');el.classList.add('leaving');
    Promise.all(el.getAnimations().map(a=>a.finished)).then(()=>{if(el.classList.contains('leaving'))el.hidden=true;}).catch(()=>{});
  }
  function syncDraft(){
    input.style.height='44px';input.style.height=Math.min(116,input.scrollHeight)+'px';
    const has=!!input.value.trim(), button=q('.send'), glyph=state.busy?'square':has?'arrow-up':'mic';
    button.classList.toggle('has-text',has&&!state.busy);
    if(button.dataset.glyph!==glyph){button.innerHTML=icon(glyph);button.dataset.glyph=glyph;}
    button.setAttribute('aria-label',state.busy?'Cancel answer':has?'Send message':'Dictate a message');
    button.disabled=!state.ready||state.deleting;
    q('[data-act=attach]').disabled=!state.ready||state.deleting;
  }
  function setDraft(text){localDraft=text;input.value=text;draftVersion++;transport('draft',{text,revision:draftVersion});syncDraft();}
  function card(note,act='note'){
    return `<button class="note-card" data-act="${act}" data-id="${escape(note.id)}"${act==='attach-note'&&!note.attachable?' disabled':''}><strong>${escape(note.title)}</strong><p>${escape(act==='attach-note'?note.attachable?note.metadata:'Available after synchronization':note.preview)}</p>${act==='attach-note'?'':`<time>${escape(note.metadata)}</time>`}</button>`;
  }
  function actions(note,rows=false){
    return ['delete','share','copy'].filter(a=>a!=='delete'||!note.active).map(a=>`<button class="${rows?'row':''}" data-act="${a}-note" data-id="${escape(note.id)}" aria-label="${a[0].toUpperCase()+a.slice(1)}">${icon(a==='delete'?'trash':a)}${rows?`<span>${a[0].toUpperCase()+a.slice(1)}</span>`:''}</button>`).join('');
  }
  function library(){
    const key=JSON.stringify(state.notes);if(key===lastLibrary)return;lastLibrary=key;
    const scroll=q('.library-scroll'),search=q('.note-search'),term=search.querySelector('input').value;
    scroll.querySelectorAll('.group,.note-wrap,.empty-search').forEach(e=>e.remove());
    let day='';state.notes.forEach(n=>{if(day!==n.day){day=n.day;const h=document.createElement('div');h.className='group';h.textContent=day;scroll.append(h);}
      const wrap=document.createElement('div');wrap.className='note-wrap';wrap.dataset.id=n.id;
      wrap.innerHTML=`<div class="note-actions" inert>${actions(n)}</div>${card(n)}`;scroll.append(wrap);
    });
    const empty=document.createElement('p');empty.className='empty-search';scroll.append(empty);filterNotes(term);
  }
  function filterNotes(term){
    term=term.trim().toLowerCase();let count=0;
    q('.library').querySelectorAll('.note-wrap').forEach(w=>{const n=state.notes.find(n=>n.id===w.dataset.id);w.hidden=!`${n.title} ${n.preview} ${n.search||''}`.toLowerCase().includes(term);if(!w.hidden)count++;});
    q('.library').querySelectorAll('.group').forEach(g=>g.hidden=!!term);
    q('.empty-search').hidden=count>0;q('.empty-search').textContent=state.notes.length?'No notes match yet. Try another word.':'Your conversations will find a home here. Tap + with Ellis to capture your first conversation.';
  }
  function renderMessages(){
    const nearEnd=chat.scrollHeight-chat.scrollTop-chat.clientHeight<90;
    const messages=[...(state.showWelcome===false?[]:[{id:'welcome',text:'Hey, good to see you.'},{id:'welcome-2',text:'What’s on your mind?'}]),...state.messages];
    const ids=new Set(messages.map(m=>m.id));
    chat.querySelectorAll('[data-message]').forEach(e=>{if(!ids.has(e.dataset.message))e.remove();});
    let anchor=q('.day');
    messages.forEach((m,index)=>{
      let el=[...chat.querySelectorAll('[data-message]')].find(e=>e.dataset.message===m.id);
      if(!el){el=document.createElement('div');el.dataset.message=m.id;el.className='bubble context-copy'+(m.user?' user':'');}
      if(el.textContent!==m.text)el.textContent=m.text;
      if(!(index<2&&m.id.startsWith('welcome'))&&anchor===q('.day'))anchor=q('.hint');
      if(anchor.nextElementSibling!==el)anchor.after(el);
      anchor=m.id==='welcome-2'?q('.hint'):el;
    });
    q('.hint').hidden=state.showWelcome===false;q('.day').hidden=state.showWelcome===false;
    let thinking=q('.thinking');if(!thinking){thinking=document.createElement('div');thinking.className='thinking';thinking.setAttribute('role','status');chat.append(thinking);}
    thinking.textContent=state.busy?'Ellis is thinking…':'';thinking.hidden=!state.busy;
    let recovery=q('.recovery');if(!recovery){recovery=document.createElement('button');recovery.className='sample recovery';recovery.dataset.act='recover';recovery.textContent='Check reply';chat.append(recovery);}recovery.hidden=!state.uncertain;
    let earlier=q('.earlier');if(!earlier){earlier=document.createElement('button');earlier.className='sample earlier';earlier.dataset.act='earlier';earlier.textContent='Earlier messages';chat.prepend(earlier);}earlier.hidden=!state.hasEarlier;
    if(nearEnd)chat.scrollTop=chat.scrollHeight;
  }
  function renderPanel(animateContent=false){
    if(!page)return;
    const n=state.notes.find(n=>n.id===selected);let title='',html='';
    if(page==='attach') {title='Bring a note into the conversation';html=state.notes.length?state.notes.map(n=>card(n,'attach-note')).join(''):'<h3>No notes yet</h3><p>Capture a conversation to create your first note.</p>';}
    if(page==='invite'){title='Invite a friend';html=`<h1>A little more company.</h1><p>Friend invitations aren’t available in this internal build yet.</p><button class="row" data-act="profile">Your profile ${icon('chevron-right')}</button>`;}
    if(page==='profile'){title='Your space';html=`<h1>Good to have you here.</h1><div class="paper"><button class="row" data-act="theme">Appearance <span>${escape(state.appearance)}</span></button><button class="row" data-act="privacy">What Ellis remembers ${icon('chevron-right')}</button></div>`;}
    if(page==='privacy'){title='What Ellis remembers';html=`<h1>You’re in control.</h1><p>Ellis uses your captured conversations to remember relevant context.</p><button class="row" data-act="memory" role="switch" aria-checked="${state.useMemory}">Use past memory <span>${state.useMemory?'On':'Off'}</span></button><p>Deleting a note removes its transcript. Existing replies and learned memories may remain.</p>`;}
    if(page==='note'||page==='transcript'){
      if(!n){close();return;}const detail=state.detail?.id===selected?state.detail:null,live=page==='transcript';
      title=live?'Live transcript':'Your note';
      html=live?'<p class="subtitle">Transcribing live · speaker labels are estimates</p>':`<h1>${escape(n.title)}</h1><p class="subtitle">${escape(n.metadata)}</p><div class="segment"><button data-act="note-tab" aria-pressed="${!transcript}" class="${transcript?'':'active'}">Notes</button><button data-act="transcript-tab" aria-pressed="${transcript}" class="${transcript?'active':''}">Transcript</button></div>`;
      html+='<div class="note-content">';
      if(live||transcript||n.personal){if(detail?.passage)html+=`<div class="paper"><small>${escape(detail.passage.label)}</small><p>${escape(detail.passage.text)}</p></div>`;html+='<div class="paper">'+(detail?.transcript?.length?detail.transcript.map(p=>`<p>${n.personal?'':`<small>${escape(p.label)}</small><br>`}${escape(p.text)}</p>`).join(''): '<p>Transcript will appear here as speech is received.</p>')+'</div>';}
      else if(detail?.notes){html+='<div class="paper">'+detail.notes.map(p=>p.heading?`<h3>${escape(p.heading)}</h3>`:`<p class="note-paragraph" data-passages="${escape(JSON.stringify(p.passages||[]))}">${escape(p.text)}</p>`).join('')+'</div>';}
      else{html+=`<p>${escape(detail?.status||'Preparing notes…')}</p><button class="row" data-act="refresh-note">Refresh notes</button>${detail?.retryable?'<button class="row" data-act="retry-note">Retry notes</button>':''}`;}
      if(live)html+=`<button class="primary" data-act="end"${state.capture?.canStop?'':' disabled'}>Stop recording</button>`;
      else html+=`<button class="primary" data-act="ask-note"${n.attachable?'':' disabled'}>Talk about this</button>${n.attachable?'':'<p class="subtitle">This note isn’t ready to attach yet.</p>'}`;
      html+='</div>';
    }
    if(page==='note-actions'&&n){title=n.title;html=actions(n,true);}
    if(page==='delete-confirm'&&n){title='Delete this note?';html=`<p>The note and transcript will be removed. Your conversation and learned memories will stay.</p><button class="primary" data-act="confirm-delete" data-id="${escape(n.id)}">Delete note</button><button class="row" data-act="close">Cancel</button>`;}
    if(page==='message-actions'){title='Message';html=`<button class="row" data-act="copy-message" data-id="${escape(selected)}">${icon('copy')}<span>Copy</span></button>`;}
    if(page==='conversation-actions'){title='Conversation';html='<button class="row" data-act="refresh">Refresh conversation</button>';}
    const key=title+html;if(key===lastPanel)return;
    const previousTop=q('.panel').scrollTop,wasOpen=!overlay.hidden&&!overlay.classList.contains('leaving');
    const sheet=q('.panel');
    if(wasOpen&&page==='note'&&sheet.dataset.noteId===selected&&q('.note-content')&&q('.segment')){
      const template=document.createElement('template');template.innerHTML=html;
      q('.note-content').innerHTML=template.content.querySelector('.note-content').innerHTML;
      const segment=q('.segment');segment.classList.toggle('transcript-selected',transcript);
      segment.querySelectorAll('button').forEach(button=>{const active=(button.dataset.act==='transcript-tab')===transcript;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});
      if(animateContent&&!matchMedia('(prefers-reduced-motion:reduce)').matches)q('.note-content').animate([{opacity:0,transform:'translateY(6px)'},{opacity:1,transform:'translateY(0)'}],{duration:560,easing:'cubic-bezier(.22,.65,.28,1)'});
    }
    else if(wasOpen){q('.panel-head h2').textContent=title;q('.panel').setAttribute('aria-label',title);q('.panel-body').innerHTML=html;icons();q('.panel').scrollTop=previousTop;}
    else panel(title,html);
    sheet.dataset.page=page;sheet.dataset.noteId=selected||'';
    q('.segment')?.classList.toggle('transcript-selected',transcript);
    lastPanel=key;
  }
  function open(which,id=null){page=which;selected=id;lastPanel='';renderPanel();}
  function renderDictation(){
    const d=state.dictation, composer=q('.composer');let row=q('.dictation-row');
    if(!row){row=document.createElement('div');row.className='dictation-row';composer.append(row);}
    [q('.clip'),input,q('.send')].forEach(e=>e.hidden=!!d);row.hidden=!d;
    if(!d)return;
    if(!row.firstChild)row.innerHTML=`<button data-act="discard-dictation" aria-label="Discard dictation">${icon('trash')}</button><span class="dictation-time"></span><div class="dictation-wave" aria-hidden="true"></div><button data-act="send-dictation" class="send has-text" aria-label="Send dictation">${icon('arrow-up')}</button>`;
    row.querySelector('.dictation-time').textContent=d.status==='listening'?d.time:d.status==='starting'?'Starting…':'Finishing…';
    row.querySelector('[data-act=send-dictation]').disabled=d.status!=='listening';
    row.querySelector('.dictation-wave').innerHTML=d.levels.map(v=>`<span style="height:${Math.max(3,Math.min(28,v*28))}px"></span>`).join('');
  }
  function render(next){
    state=next;device.style.colorScheme=state.appearance==='system'?'light dark':state.appearance;
    if(next.draftVersion>=draftVersion&&input.value!==next.draft){localDraft=next.draft;input.value=next.draft;draftVersion=next.draftVersion;}
    renderMessages();library();syncDraft();renderDictation();
    const c=state.capture;device.classList.toggle('listening',!!c);device.classList.toggle('quiet',!!c?.quiet);
    q('.capture').hidden=!c;q('.plus').hidden=!!c;q('.plus').disabled=!state.ready||state.deleting||!!state.dictation;
    if(c){q('.capture-word').textContent=c.label;q('.capture time').textContent=c.time;q('[data-act=end]').disabled=!c.canStop;
      const quiet=q('[data-act=quiet]');quiet.disabled=!c.canQuiet;quiet.innerHTML=icon(c.quiet?'bell-off':'bell');quiet.setAttribute('aria-pressed',String(c.quiet));}
    q('.attachment').hidden=!state.attachment;q('.attachment span').textContent=state.attachment?.title||'';
    if(state.notice&&`${state.noticeSequence}:${state.notice}`!==lastToast){lastToast=`${state.noticeSequence}:${state.notice}`;toast(state.notice,state.persistentNotice!==false);}else if(!state.notice)lastToast='';
    renderPanel();
  }
  // Stable keyed bubbles do not replay their entrance animation for every token or meter tick.
  chat.querySelectorAll('.bubble').forEach(e=>e.remove());
  input.addEventListener('input',()=>setDraft(input.value));
  input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();q('[data-act=send]').click();}});
  q('.note-search input').addEventListener('input',e=>filterNotes(e.target.value));
  q('.persona').setAttribute('role','button');q('.persona').setAttribute('tabindex','0');q('.persona').setAttribute('aria-label','Your profile');q('.persona').dataset.act='profile';
  q('.persona').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open('profile');}});
  root.addEventListener('click',e=>{
    if(Date.now()<suppressedClickUntil){e.preventDefault();return;}
    const button=e.target.closest('[data-act]');if(!button||button.disabled)return;
    const a=button.dataset.act,id=button.dataset.id;transport('haptic');
    if(a==='close')close();if(a==='dismiss-toast')dismissToast();
    if(a==='notes'||a==='chat'){tab(a==='notes');if(a==='notes')transport('interrupt-dictation');}
    if(a==='focus-search')tab(true,true);
    if(a==='invite'){input.blur();transport('start');}
    if(a==='end'){transport('stop');if(page==='transcript')close();}
    if(a==='quiet')transport('quiet');
    if(a==='attach'){transport('library');open('attach');}
    if(a==='invite-friends')open('invite');if(a==='profile')open('profile');if(a==='privacy')open('privacy');
    if(a==='theme'){transport('appearance',{value:state.appearance==='dark'?'light':'dark'});close();}
    if(a==='memory')transport('memory',{value:!state.useMemory});
    if(a==='detach')transport('detach');
    if(a==='send'){
      if(state.busy){transport('cancel');return;}
      if(input.value.trim()){transport('send',{text:input.value,revision:draftVersion});input.blur();}
      else {input.blur();transport('dictate');}
    }
    if(a==='send-dictation')transport('send-dictation');if(a==='discard-dictation')transport('discard-dictation');
    if(a==='recover')transport('recover');if(a==='earlier')transport('earlier');
    if(a==='refresh'){transport('refresh');close();}
    if(a==='note'){transcript=false;transport('open-note',{id});open('note',id);}
    if(a==='transcript'){selected=state.capture?.id;if(selected){transport('open-note',{id:selected});open('transcript',selected);}}
    if(a==='note-tab'||a==='transcript-tab'){if(transcript!==(a==='transcript-tab')){transcript=a==='transcript-tab';renderPanel(true);}}
    if(a==='refresh-note'||a==='retry-note')transport(a,{id:selected});
    if(a==='attach-note'||a==='ask-note'){transport('attach',{id:id||selected});close();tab(false);}
    if(a==='delete-note')open('delete-confirm',id);
    if(a==='confirm-delete'){transport('delete',{id});close();}
    if(a==='share-note'||a==='copy-note'){transport(a,{id});if(page)close();const wrap=q(`.note-wrap[data-id="${CSS.escape(id)}"]`);if(wrap)settleNote(wrap,false);}
    if(a==='copy-message'){transport('copy-message',{id});close();}
  });
  // Track the finger; settle only after release. Vertical scroll never becomes a swipe.
  let gesture=null,holdTimer;
  const revealWidth=180;
  function positionNote(wrap,offset){
    const progress=Math.max(0,Math.min(1,-offset/revealWidth));
    wrap.style.setProperty('--note-offset',`${offset}px`);
    wrap.querySelectorAll('.note-actions button').forEach((button,index)=>{
      const part=Math.max(0,Math.min(1,(progress-index*.10)/.8));
      button.style.opacity=String(part);
      button.style.transform=`translateX(${(1-part)*18}px) scale(${.82+part*.18})`;
    });
  }
  function settleNote(wrap,open){
    wrap.classList.remove('dragging');wrap.classList.toggle('revealed',open);
    wrap.querySelector('.note-actions').inert=!open;
    positionNote(wrap,open?-revealWidth:0);
  }
  root.addEventListener('pointerdown',e=>{
    if(!e.isPrimary||e.button!==0)return;
    suppressedClickUntil=0;
    if(e.target.closest('button,[role=button]'))transport('prepare-haptic');
    const navigate=overlay.hidden&&!device.classList.contains('notes-open')&&!!e.target.closest('.chat')&&!e.target.closest('button,a,input,textarea');
    const target=e.target.closest('.note-card,.bubble,.persona,.note-paragraph')||(navigate?chat:null);if(!target)return;
    if(navigate)transport('prepare-haptic');
    const wrap=target.closest('.note-wrap');
    root.querySelectorAll('.note-wrap.revealed').forEach(other=>{if(other!==wrap)settleNote(other,false);});
    const start=wrap?new DOMMatrixReadOnly(getComputedStyle(target).transform).m41:0;
    gesture={target,wrap,navigate,x:e.clientX,y:e.clientY,pointer:e.pointerId,moved:false,axis:null,start,offset:start,lastX:e.clientX,lastTime:e.timeStamp,velocity:0,wasOpen:!!wrap?.classList.contains('revealed')};
    holdTimer=setTimeout(()=>{
      if(!gesture||gesture.moved||target===chat)return;suppressedClickUntil=Date.now()+600;transport('haptic');
      if(wrap)open('note-actions',wrap.dataset.id);
      else if(target.matches('.bubble'))open('message-actions',target.dataset.message);
      else if(target.matches('.persona'))open('conversation-actions');
      else if(target.matches('.note-paragraph')){const passages=JSON.parse(target.dataset.passages||'[]');if(passages.length){transport('passage',{id:selected,passage:passages[0]});transcript=true;renderPanel();}}
      gesture=null;
    },550);
  });
  root.addEventListener('pointermove',e=>{
    if(!gesture||e.pointerId!==gesture.pointer)return;
    const g=gesture,dx=e.clientX-g.x,dy=e.clientY-g.y;
    if(Math.abs(dx)>8||Math.abs(dy)>8){g.moved=true;clearTimeout(holdTimer);}
    if(!g.axis&&g.moved)g.axis=Math.abs(dx)>Math.abs(dy)*1.4?'x':'y';
    if(g.axis==='x'&&g.navigate){suppressedClickUntil=Date.now()+600;return;}
    if(g.axis!=='x'||!g.wrap)return;
    if(!g.wrap.classList.contains('dragging')){
      g.wrap.classList.add('dragging');g.wrap.querySelector('.note-actions').inert=true;
      g.target.setPointerCapture?.(e.pointerId);
    }
    const delta=e.timeStamp-g.lastTime;
    if(delta>0)g.velocity=(e.clientX-g.lastX)/delta;
    g.lastX=e.clientX;g.lastTime=e.timeStamp;
    g.offset=Math.max(-revealWidth,Math.min(0,g.start+dx));
    positionNote(g.wrap,g.offset);suppressedClickUntil=Date.now()+600;
  });
  function endGesture(e){
    clearTimeout(holdTimer);const g=gesture;if(!g||e.pointerId!==g.pointer)return;
    if(g.navigate&&g.axis==='x'&&e.type==='pointerup'&&e.clientX-g.x<-64){
      tab(true);transport('interrupt-dictation');transport('haptic');
    }
    if(g.axis==='x'&&g.wrap){
      const velocity=e.timeStamp-g.lastTime<100?g.velocity:0;
      const open=e.type==='pointercancel'?g.wasOpen:Math.abs(velocity)>.45?velocity<0:g.offset<-revealWidth*.45;
      settleNote(g.wrap,open);
      if(open!==g.wasOpen&&e.type!=='pointercancel')transport('haptic');
    }
    if(g.moved)suppressedClickUntil=Date.now()+400;gesture=null;
  }
  root.addEventListener('pointerup',endGesture);root.addEventListener('pointercancel',endGesture);
  root.addEventListener('contextmenu',e=>{if(e.target.closest('.note-card,.bubble,.persona'))e.preventDefault();});
  overlay.addEventListener('click',e=>{if(e.target===overlay)close();});
  root.addEventListener('keydown',e=>{if(e.key==='Escape'){if(!overlay.hidden)close();else tab(false);}
    if(e.key==='Tab'&&!overlay.hidden){const els=[...overlay.querySelectorAll('button:not(:disabled),[tabindex="0"]')];if(e.shiftKey&&document.activeElement===els[0]){e.preventDefault();els.at(-1)?.focus();}else if(!e.shiftKey&&document.activeElement===els.at(-1)){e.preventDefault();els[0]?.focus();}}
  });
  window.room={render,toast};icons();
  // This adapter is only reachable in a browser without the native message handler.
  // It cannot record audio, call a provider, or mutate personal data.
  function preview(command){
    const a=command.action;
    if(a==='draft'){state.draft=command.text;state.draftVersion=command.revision;}
    if(a==='appearance')state.appearance=command.value;if(a==='memory')state.useMemory=command.value;
    if(a==='send'){state.messages.push({id:crypto.randomUUID(),text:command.text,user:true});state.draft='';state.draftVersion=command.revision;state.busy=true;
      setTimeout(()=>{state.busy=false;state.messages.push({id:crypto.randomUUID(),text:'Sounds like you’re deciding what comes first.'});render(state);},1000);}
    if(a==='cancel')state.busy=false;
    if(a==='start')state.capture={id:'sample',label:'Listening',time:'0:00',canStop:true,canQuiet:true,quiet:false};
    if(a==='quiet'&&state.capture)state.capture.quiet=true;
    if(a==='stop')state.capture=null;
    if(a==='attach'){const n=state.notes.find(n=>n.id===command.id);state.attachment=n?{id:n.id,title:n.title}:null;}
    if(a==='detach')state.attachment=null;
    if(a==='open-note'){state.detail={id:command.id,notes:[{heading:'Try the simple version first.'},{text:'Test the recording flow with five people before adding features.'},{heading:'What comes next'},{text:'Compare feedback on Friday. Calendar integration can wait until after the test.'}],transcript:[{label:'00:18 · Speaker 1',text:'Let’s test the basic recording flow with five people first.'}]};}
    if(a==='delete')state.notes=state.notes.filter(n=>n.id!==command.id);
    if(a==='dictate'||a==='share-note'||a==='copy-note'||a==='copy-message')toast('Design preview — no device action');
    if(a==='refresh')toast('Preview conversation is up to date.');
    if(a!=='haptic')render(state);
  }
  if(native)transport('ready');else{
    state={...state,ready:true,useMemory:true,notes:[{id:'sample',title:'A small test, then build',preview:'Try the recording flow with five people before adding more features.',day:'Today',metadata:'10:24 AM · 12 min',attachable:true},{id:'walk',title:'A walk with Sam',preview:'A quieter week, and a little more room to think.',day:'Yesterday',metadata:'4:15 PM · 18 min',attachable:true}]};render(state);
  }
})();
