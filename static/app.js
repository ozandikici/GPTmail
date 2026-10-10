(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const pages = {
    inbox: 'Posta kutusu', accounts: 'E-posta hesapları', permissions: 'MCP yetkileri',
    approvals: 'Onay bekleyenler', connection: 'ChatGPT bağlantısı', activity: 'İşlem geçmişi'
  };
  let state = null;
  let currentPage = 'inbox';
  let chosen = null;
  let toastTimer;
  let selectedProvider = null;
  const providerPresets = {
    custom: ['', 993, '', 465, 'Posta hizmetinin verdiği IMAP ve SMTP adreslerini kullan.'],
    icloud: ['imap.mail.me.com', 993, 'smtp.mail.me.com', 587, 'Apple hesabında uygulamaya özel bir parola oluştur. IMAP kullanıcı adı, e-posta adresinin @ öncesindeki kısmı olabilir.'],
    yahoo: ['imap.mail.yahoo.com', 993, 'smtp.mail.yahoo.com', 465, 'Yahoo hesap güvenliği bölümünde bir uygulama şifresi oluştur.'],
    zoho: ['imap.zoho.com', 993, 'smtp.zoho.com', 465, 'Zoho sunucuları bölgeye ve hesap türüne göre değişir. Kurumsal hesaplar imappro/smtppro kullanabilir. Hesap ayarlarındaki adresleri doğrula; IMAP planına bağlıdır.'],
    fastmail: ['imap.fastmail.com', 993, 'smtp.fastmail.com', 465, 'Fastmail uygulama şifresi kullan. Planın IMAP/SMTP erişimini desteklemelidir.'],
    gmail: ['imap.gmail.com', 993, 'smtp.gmail.com', 465, 'Yalnızca Google hesabın uygulama şifresi oluşturmaya izin veriyorsa kullan. Diğer hesaplar için yukarıdaki Google OAuth bağlantısını seç.']
  };

  const create = (name, className, text) => {
    const el = document.createElement(name);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = String(text);
    return el;
  };
  const clear = (node) => { node.replaceChildren(); return node; };
  const notice = (message, error = false) => {
    const node = $('toast'); node.textContent = message; node.className = 'visible' + (error ? ' error' : '');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => node.className = '', 4800);
  };
  const api = async (url, payload) => {
    const response = await fetch(url, {
      method: payload === undefined ? 'GET' : 'POST',
      credentials: 'same-origin',
      headers: payload === undefined ? {} : { 'Content-Type': 'application/json' },
      body: payload === undefined ? undefined : JSON.stringify(payload)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : data.detail?.code === 'setup_required' ? 'Sağlayıcı OAuth uygulaması henüz yapılandırılmadı. Kurulum rehberini takip et.' : 'İstek başarısız. (' + response.status + ')');
    return data;
  };
  const action = async (name, data = {}) => (await api('/api/admin/action', { action: name, data })).data;
  const run = async (operation, errorMessage) => {
    try { await operation(); } catch (error) { notice(error.message || errorMessage || 'İşlem tamamlanamadı.', true); }
  };
  const date = (value) => { try { return new Date(value).toLocaleString('tr-TR'); } catch { return value || ''; } };
  const accountName = (id) => state?.accounts?.find(x => x.id === id)?.name || id;

  function navigate(page) {
    currentPage = page;
    for (const name of Object.keys(pages)) $('page-' + name).classList.toggle('hidden', name !== page);
    for (const btn of document.querySelectorAll('#nav [data-page]')) btn.classList.toggle('active', btn.dataset.page === page);
    $('pageTitle').textContent = pages[page];
  }

  async function refreshState() {
    state = await api('/api/admin/state');
    $('loginView').classList.add('hidden'); $('workspace').classList.remove('hidden');
    renderAccounts(); renderProviders(); renderPermissions(); renderApprovals(); renderConnection(); renderAudit();
    $('accountCount').textContent = `${state.accounts.length} HESAP BAĞLI`;
    $('onboardingCard').classList.toggle('hidden', state.accounts.length > 0);
    const pending = state.pending?.length || 0;
    $('pendingCount').textContent = pending;
    $('pendingCount').classList.toggle('hidden', pending === 0);
  }

  function showProvider(provider, account = null) {
    selectedProvider = provider;
    $('oauthConnectPanel').classList.remove('hidden');
    $('oauthProviderTitle').textContent = `${provider.name} ile ${account ? 'yeniden bağlan' : 'bağlan'}`;
    $('oauthProviderNote').textContent = 'Şifren sağlayıcıda kalır. Erişimi sağlayıcının onay ekranında verirsin; bağlantı anahtarları sunucuda şifreli saklanır.';
    $('oauthSetup').classList.toggle('hidden', provider.configured);
    $('oauthConnectForm').classList.toggle('hidden', !provider.configured);
    $('oauthMissing').textContent = 'Dağıtım ayarlarında eksik: ' + (provider.missing_env || []).join(', ') + '. Anahtarları bu panele veya sohbete yazma; Vercel ortam değişkenlerine ekle.';
    $('oauthRedirect').textContent = provider.redirect_uri || '';
    const form = $('oauthConnectForm'); form.reset();
    form.elements.namedItem('email').value = account?.email || '';
    form.elements.namedItem('name').value = account?.name || '';
    $('oauthConnectPanel').scrollIntoView({behavior:'smooth',block:'center'});
  }

  function renderProviders() {
    const cards = clear($('providerCards'));
    for (const provider of state.providers || []) {
      const card = create('button', 'provider-card'); card.type = 'button';
      card.append(create('span', 'provider-symbol', provider.id === 'google' ? 'G' : provider.id === 'microsoft' ? 'M' : '@'),
        create('span', 'provider-arrow', '↗'), create('h3', '', provider.id === 'imap' ? 'Diğer posta hesapları' : provider.name),
        create('p', '', provider.id === 'google' ? 'Gmail & Google Workspace' : provider.id === 'microsoft' ? 'Outlook, Hotmail & Microsoft 365' : 'iCloud, Yahoo, Zoho, Fastmail ve özel alan adları'),
        create('span', 'provider-state', provider.auth_type === 'oauth' ? provider.configured ? 'OAuth · Bağlamaya hazır' : 'OAuth · Uygulama kurulumu gerekli' : 'IMAP / SMTP · Şifre veya uygulama şifresi'));
      card.addEventListener('click', () => {
        if (provider.auth_type === 'oauth') showProvider(provider);
        else { resetAccountForm(); $('oauthConnectPanel').classList.add('hidden'); $('imapPanel').scrollIntoView({behavior:'smooth',block:'start'}); }
      }); cards.append(card);
    }
  }

  function renderAccounts() {
    const prev = $('inboxAccount').value;
    clear($('inboxAccount')).append(create('option', '', 'Hesap seç'));
    $('inboxAccount').firstChild.value = '';
    for (const a of state.accounts) {
      const opt = create('option', '', `${a.name} — ${a.email}`); opt.value = a.id; $('inboxAccount').append(opt);
    }
    $('inboxAccount').value = state.accounts.some(x => x.id === prev) ? prev : (state.accounts[0]?.id || '');
    const list = clear($('accountList'));
    list.classList.toggle('empty', state.accounts.length === 0);
    if (!state.accounts.length) { list.textContent = 'Henüz hesap eklenmedi.'; return; }
    for (const a of state.accounts) {
      const box = create('div', 'account-item');
      box.append(create('span', 'account-provider', a.auth_type === 'oauth' ? `${a.provider === 'google' ? 'Google' : 'Microsoft'} · OAuth` : 'IMAP / SMTP'));
      box.append(create('h4', '', a.name), create('p', '', a.email),
                 create('p', '', `${a.imap_host}:${a.imap_port} · ${a.smtp_status === 'unavailable' ? 'SMTP erişimi doğrulanamadı' : a.smtp_host ? 'SMTP yapılandırıldı' : 'SMTP kapalı'}`));
      if (a.connection_status === 'reconnect_required') box.append(create('p', 'provider-hint', 'Erişim sona erdi. Hesabı yeniden bağla.'));
      const access = create('label', 'permission-row');
      const toggle = create('input'); toggle.type = 'checkbox'; toggle.checked = a.mcp_enabled !== false;
      access.append(toggle, create('span', '', 'Bu hesaba ChatGPT erişebilsin'));
      toggle.addEventListener('change', () => run(async () => {
        await action('account/access', { account_id: a.id, mcp_enabled: toggle.checked });
        await refreshState(); notice('Hesap MCP erişimi güncellendi.');
      }));
      box.append(access);
      const actions = create('div', 'account-item-actions');
      const edit = create('button', 'secondary', 'Düzenle');
      edit.addEventListener('click', () => {
        if (a.auth_type === 'oauth') {
          const provider = state.providers?.find(p => p.id === a.provider);
          if (provider) showProvider(provider, a);
          return;
        }
        const form = $('accountForm');
        for (const field of ['name','email','imap_host','imap_port','username','smtp_host','smtp_port','smtp_username']) {
          form.elements.namedItem(field).value = a[field] ?? '';
        }
        form.elements.namedItem('account_id').value = a.id;
        form.elements.namedItem('password').value = '';
        form.elements.namedItem('password').required = false;
        form.elements.namedItem('smtp_password').value = '';
        form.querySelector('[type=submit]').textContent = 'Değişiklikleri doğrula ve kaydet';
        $('cancelAccountEdit').classList.remove('hidden');
        form.scrollIntoView({behavior:'smooth',block:'start'});
      });
      if (a.auth_type === 'oauth') edit.textContent = 'Yeniden bağlan';
      actions.append(edit);
      const test = create('button', 'secondary', 'Bağlantıyı test et');
      test.addEventListener('click', () => run(async () => {
        test.disabled = true;
        try { const out = await action('account/test', { account_id: a.id });
          await refreshState();
          notice(`IMAP: ${out.imap ? 'OK' : 'HATA'} / SMTP: ${out.smtp === null ? 'yapılandırılmadı' : out.smtp ? 'OK' : 'HATA'}`);
        } finally { test.disabled = false; }
      }));
      const remove = create('button', 'danger-outline', 'Hesabı kaldır');
      remove.addEventListener('click', () => run(async () => {
        if (!confirm(`${a.email} hesabını GPTmail'den kaldırmak istiyor musun? Posta sunucusundaki mailler silinmeyecek.`)) return;
        await action('account/remove', { account_id: a.id });
        await refreshState(); notice('Hesap kaldırıldı.');
      }));
      actions.append(test, remove); box.append(actions); list.append(box);
    }
  }

  function renderPermissions() {
    const list = clear($('permissionList'));
    for (const [key, label] of Object.entries(state.permission_labels)) {
      const row = create('label', 'permission-row' + (['delete', 'send', 'send_approval', 'delete_approval'].includes(key) ? ' critical' : ''));
      const input = create('input'); input.type = 'checkbox'; input.dataset.permission = key;
      input.checked = Boolean(state.permissions[key]);
      row.append(input, create('span', '', label)); list.append(row);
    }
  }

  function renderApprovals() {
    const list = clear($('approvalList'));
    if (!state.pending.length) { list.append(create('div', 'panel empty', 'Onay bekleyen işlem bulunmuyor.')); return; }
    for (const item of state.pending) {
      const box = create('div', 'approval-card');
      box.append(create('h3', '', item.action === 'send' ? 'Giden e-posta onayı' : 'Çöp kutusuna taşıma onayı'));
      box.append(create('p', '', `${accountName(item.account_id)} · ${date(item.created_at)}`));
      if (item.action === 'send') {
        box.append(create('p', '', `Alıcı: ${(item.message?.to || []).join(', ')}`));
        box.append(create('p', '', `Konu: ${item.message?.subject || '(boş)'}`));
        box.append(create('pre', '', item.message?.body || ''));
      } else {
        box.append(create('p', '', `Klasör: ${item.folder} · UID: ${item.uid}`));
      }
      const controls = create('div', 'approval-actions');
      const approve = create('button', 'primary', 'Onayla ve uygula');
      approve.addEventListener('click', () => run(async () => {
        if (!confirm('Bu işlem gerçek e-posta hesabında uygulanacak. Devam edilsin mi?')) return;
        approve.disabled = true;
        try { await action('approval/approve', { id: item.id }); await refreshState(); notice('Onaylanan işlem uygulandı.'); }
        finally { approve.disabled = false; }
      }));
      const reject = create('button', 'secondary', 'Reddet');
      reject.addEventListener('click', () => run(async () => {
        await action('approval/reject', { id: item.id }); await refreshState(); notice('Talep reddedildi.');
      }));
      controls.append(approve, reject); box.append(controls); list.append(box);
    }
  }

  function renderConnection() { $('mcpUrl').textContent = state.mcp_url; }

  function renderAudit() {
    const list = clear($('auditList'));
    if (!state.audit.length) { list.append(create('div', 'empty', 'Henüz işlem kaydı yok.')); return; }
    for (const item of state.audit) {
      const row = create('div', 'audit-row'); const d = create('time', '', date(item.at));
      row.append(d, create('b', '', item.action + (item.account_id ? ` · ${accountName(item.account_id)}` : '')),
                 create('span', '', item.status)); list.append(row);
    }
  }

  async function refreshFolders() {
    const id = $('inboxAccount').value;
    if (!id) return;
    const folders = await action('mail/folders', { account_id: id });
    const select = clear($('inboxFolder'));
    for (const f of folders) {
      if (f.flags.includes('\\Noselect')) continue;
      const opt = create('option', '', f.name); opt.value = f.name; select.append(opt);
    }
    if (folders.find(f => f.name.toUpperCase() === 'INBOX')) select.value = 'INBOX';
    await loadMessages();
  }

  async function loadMessages(query) {
    const id = $('inboxAccount').value;
    const list = clear($('messagesList')); $('messageDetail').textContent = 'Bir mesaj seçtiğinde burada görüntülenecek.';
    chosen = null;
    if (!id) { list.className = 'empty'; list.textContent = 'Önce bir e-posta hesabı ekle.'; return; }
    list.className = 'empty'; list.textContent = 'Mesajlar getiriliyor...';
    const folder = $('inboxFolder').value || 'INBOX';
    const rows = query ? await action('mail/search', { account_id: id, folder, query, limit: 40 })
                       : await action('mail/list', { account_id: id, folder, limit: 40 });
    clear(list); list.className = '';
    if (!rows.length) { list.className = 'empty'; list.textContent = 'Mesaj bulunamadı.'; return; }
    for (const msg of rows) {
      const row = create('button', 'mail-row' + (msg.seen ? '' : ' unread')); row.type = 'button';
      const title = create('div', 'mail-title'); title.append(create('strong', '', msg.from || 'Bilinmeyen gönderici'),
                                                          create('span', '', msg.date?.substring(0, 20) || ''));
      row.append(title, create('p', '', msg.subject || '(konu yok)'));
      row.addEventListener('click', () => run(async () => {
        document.querySelectorAll('.mail-row').forEach(el => el.classList.remove('selected'));
        row.classList.add('selected'); chosen = { ...msg, account_id: id, folder };
        const read = await action('mail/read', { account_id: id, folder, uid: msg.uid });
        renderMessage(read);
      }));
      list.append(row);
    }
  }

  function renderMessage(msg) {
    const detail = clear($('messageDetail')); detail.className = '';
    const header = create('div', 'mail-header'); header.append(create('h3', '', msg.subject || '(konu yok)'));
    header.append(create('p', '', `Kimden: ${msg.from}`), create('p', '', `Kime: ${msg.to}`), create('p', '', `Tarih: ${msg.date}`));
    detail.append(header);
    const actions = create('div', 'message-actions');
    const seen = create('button', 'secondary', chosen?.seen ? 'Okunmadı işaretle' : 'Okundu işaretle');
    seen.addEventListener('click', () => run(async () => {
      await action('mail/mark', { account_id: chosen.account_id, folder: chosen.folder, uid: chosen.uid,
                                 flag: 'seen', enabled: !chosen.seen });
      await loadMessages(); notice('Mesaj durumu güncellendi.');
    }));
    const trash = create('button', 'danger-outline', 'Çöp kutusuna taşı');
    trash.addEventListener('click', () => run(async () => {
      if (!confirm('Bu mesaj çöp kutusuna taşınacak. Devam?')) return;
      await action('mail/delete', { account_id: chosen.account_id, folder: chosen.folder, uid: chosen.uid });
      await loadMessages(); notice('Mesaj çöp kutusuna taşındı.');
    }));
    actions.append(seen, trash); detail.append(actions);
    detail.append(create('div', 'message-body', msg.body || '(Mesaj metni bulunamadı.)'));
    for (const item of msg.attachments || []) detail.append(create('span', 'attachment-chip', `${item.filename} · ${Math.ceil(item.size / 1024)} KB`));
  }

  $('loginForm').addEventListener('submit', event => {
    event.preventDefault(); run(async () => {
      const pass = $('adminPassword').value;
      await api('/api/auth/login', { password: pass }); $('adminPassword').value = '';
      await refreshState(); navigate('inbox');
      if (state.accounts.length) await refreshFolders();
    });
  });

  $('logoutBtn').addEventListener('click', () => run(async () => {
    await api('/api/auth/logout', {});
    window.location.replace('/');
  }));
  $('addFirstAccount').addEventListener('click', () => navigate('accounts'));
  $('closeOAuth').addEventListener('click', () => $('oauthConnectPanel').classList.add('hidden'));
  $('oauthConnectForm').addEventListener('submit', event => {
    event.preventDefault(); run(async () => {
      if (!selectedProvider?.configured) throw new Error('Önce sağlayıcı OAuth uygulamasını yapılandır.');
      const submit = event.target.querySelector('[type=submit]'); submit.disabled = true;
      try {
        const result = await api(`/api/admin/providers/${selectedProvider.id}/connect`, Object.fromEntries(new FormData(event.target).entries()));
        const url = new URL(result.authorization_url);
        const expectedHost = selectedProvider.id === 'google' ? 'accounts.google.com' : 'login.microsoftonline.com';
        if (url.protocol !== 'https:' || url.hostname !== expectedHost) throw new Error('Beklenmeyen yetkilendirme adresi.');
        window.location.assign(url.href);
      } finally { submit.disabled = false; }
    });
  });
  $('providerPreset').addEventListener('change', () => {
    const selected = $('providerPreset').value;
    resetAccountForm(); $('providerPreset').value = selected;
    const values = providerPresets[selected]; const form = $('accountForm');
    ['imap_host','imap_port','smtp_host','smtp_port'].forEach((key, i) => form.elements.namedItem(key).value = values[i]);
    $('providerHint').textContent = values[4];
  });
  $('accountForm').elements.namedItem('email').addEventListener('blur', event => {
    const form = $('accountForm');
    if (!form.elements.namedItem('username').value) form.elements.namedItem('username').value = event.target.value;
    if (!form.elements.namedItem('smtp_username').value) form.elements.namedItem('smtp_username').value = event.target.value;
  });
  document.querySelectorAll('#nav [data-page]').forEach(node => node.addEventListener('click', () => navigate(node.dataset.page)));
  function resetAccountForm() {
    const form = $('accountForm'); form.reset(); form.elements.namedItem('account_id').value = '';
    form.elements.namedItem('password').required = true;
    form.querySelector('[type=submit]').textContent = 'Bağlantıyı doğrula ve kaydet';
    $('cancelAccountEdit').classList.add('hidden');
    $('providerPreset').value = 'custom'; $('providerHint').textContent = providerPresets.custom[4];
  }
  $('cancelAccountEdit').addEventListener('click', resetAccountForm);
  $('accountForm').addEventListener('submit', event => {
    event.preventDefault(); run(async () => {
      const form = $('accountForm'); const submit = form.querySelector('button[type=submit]'); submit.disabled = true;
      try {
        const values = Object.fromEntries(new FormData(form).entries());
        await action(values.account_id ? 'account/update' : 'account/add', values);
        resetAccountForm(); await refreshState(); notice('Hesap bağlantısı doğrulandı ve şifreli saklandı.');
      } finally { submit.disabled = false; }
    });
  });
  $('savePermissions').addEventListener('click', () => run(async () => {
    const changes = Object.fromEntries(Array.from(document.querySelectorAll('[data-permission]')).map(i => [i.dataset.permission, i.checked]));
    if (!changes.send_approval && (changes.send || changes.reply || changes.forward)) {
      if (!confirm('Gönderme onayı kapalı! ChatGPT yeni e-postaları onay almadan gönderebilir. Yine de kaydedilsin mi?')) return;
    }
    if (!changes.delete_approval && changes.delete) {
      if (!confirm('Silme onayı kapalı! ChatGPT mailleri doğrudan çöp kutusuna taşıyabilir. Devam?')) return;
    }
    await action('permissions/update', changes); await refreshState(); notice('MCP yetkileri güncellendi.');
  }));
  $('presetRead').addEventListener('click', () => {
    for (const input of document.querySelectorAll('[data-permission]')) {
      input.checked = ['read', 'send_approval', 'delete_approval'].includes(input.dataset.permission);
    }
  });
  $('presetAll').addEventListener('click', () => {
    for (const input of document.querySelectorAll('[data-permission]')) input.checked = true;
  });
  $('inboxAccount').addEventListener('change', () => run(refreshFolders));
  $('inboxFolder').addEventListener('change', () => run(() => loadMessages()));
  $('refreshInbox').addEventListener('click', () => run(() => loadMessages()));
  $('searchBtn').addEventListener('click', () => run(() => loadMessages($('searchQuery').value.trim())));
  $('searchQuery').addEventListener('keydown', event => { if (event.key === 'Enter') $('searchBtn').click(); });
  $('composeToggle').addEventListener('click', () => $('composePanel').classList.toggle('hidden'));
  $('closeCompose').addEventListener('click', () => $('composePanel').classList.add('hidden'));
  $('composeForm').addEventListener('submit', event => { event.preventDefault(); run(async () => {
    const id = $('inboxAccount').value;
    if (!id) throw new Error('Önce posta hesabı seç.');
    const values = Object.fromEntries(new FormData($('composeForm')).entries());
    values.to = values.to.split(',').map(s => s.trim()).filter(Boolean); values.account_id = id;
    if (!confirm(`${values.to.join(', ')} adresine gerçek e-posta gönderilsin mi?`)) return;
    const result = await action('mail/send', values);
    $('composeForm').reset(); $('composePanel').classList.add('hidden'); notice('E-posta SMTP üzerinden gönderildi.');
  }); });
  $('refreshApprovals').addEventListener('click', () => run(refreshState));
  $('copyUrl').addEventListener('click', () => run(async () => { await navigator.clipboard.writeText(state.mcp_url); notice('MCP URL kopyalandı.'); }));
  $('revokeConnections').addEventListener('click', () => run(async () => {
    if (!confirm('Tüm OAuth access/refresh tokenları geçersiz olacak. ChatGPT yeniden bağlanmak zorunda kalacak. Onaylıyor musun?')) return;
    await action('connections/revoke'); await refreshState(); notice('MCP bağlantıları geçersiz kılındı.');
  }));
  run(async () => {
    try { await refreshState();
      const query = new URLSearchParams(window.location.search);
      if (query.has('provider_connected') || query.has('provider_error')) {
        navigate('accounts');
        notice(query.has('provider_connected') ? 'Posta hesabı OAuth ile bağlandı.' : 'Sağlayıcı bağlantısı tamamlanamadı. İzinleri ve uygulama ayarlarını kontrol edip tekrar dene.', query.has('provider_error'));
        history.replaceState(null, '', '/');
      } else navigate(currentPage);
      if (state.accounts.length) await refreshFolders(); }
    catch (error) { if (String(error.message).includes('401') || error.message.includes('authentication')) return;
      if (error.message === 'Admin authentication required.') return;
      notice(error.message, true);
    }
  });
})();
