# GPTmail — tanıtım paketi / promotion kit

Hazırlanma ve kaynak kontrol tarihi: **10 Ekim 2026**. Bu dosya bir hazırlık paketidir; topluluklara gönderim yapılmamıştır. Metinleri yalnızca kullanılacak platformun kuralları izin veriyorsa kullan.

**Ana bağlantı:** [github.com/ozandikici/GPTmail](https://github.com/ozandikici/GPTmail)

## Marka

| Öğe | Kullanım |
|---|---|
| Ad | **GPTmail**; her yerde aynı yazım |
| İngilizce slogan | **Every inbox. One private workspace.** |
| Türkçe slogan | **Tüm kutuların. Tek özel alanın.** |
| Kısa tanım | Kendi kurduğun, birden çok posta hesabını yöneten ve ChatGPT'ye izin kontrollü erişim sunan açık kaynak çalışma alanı |
| Renkler | Kırık beyaz `#F4F2E9`, limon yeşili `#D5FA68`, kömür `#141813` |
| Görsel dil | Ferah alan, okunaklı tipografi, açık renk yüzeyler, yeşilin sınırlı vurgu olarak kullanımı |
| Logo dosyası | `static/brand/gptmail-mark.png` |
| Tanıtım görseli | `static/brand/gptmail-social.png` |
| Üslup | Sade, somut, kullanıcı denetimine odaklı; ölçülmemiş başarı veya güvenlik iddiası yok |

“Every inbox” bir marka hedefidir; ürün açıklamasında **uyumlu IMAP/SMTP hesapları ve yapılandırılmış Google/Microsoft OAuth** kapsamını belirt. “Tüm e-posta sağlayıcılarında koşulsuz çalışır” yazma. GPTmail bağımsız bir açık kaynak projedir; OpenAI, Google veya Microsoft'un resmî ürünü ya da onayladığı bir hizmet olarak sunulmaz.

## GitHub profil metni

**About açıklaması (EN):**

> A private email workspace and OAuth-protected MCP server for ChatGPT. Connect compatible inboxes and control each AI action. Self-hosted, MIT licensed.

**Kısa açıklama (TR):**

> Uyumlu posta hesaplarını tek özel alanda yöneten, ChatGPT erişimini ayrı ayrı yetkilendirdiğin açık kaynak e-posta çalışma alanı.

**Önerilen topics:**

```text
email imap smtp mcp mcp-server oauth chatgpt self-hosted python fastapi vercel upstash
```

Konuyla ilgili topics, projenin GitHub'da keşfedilmesine yardımcı olur; alakasız popüler etiketler ekleme. [GitHub topic rehberi](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics).

## Genel tanıtım — Türkçe

**Başlık:** GPTmail: posta hesapların ve ChatGPT için özel bir çalışma alanı

> GPTmail, uyumlu e-posta hesaplarını tek bir parola korumalı panelden yönetmek için geliştirdiğim açık kaynak proje. Kendi sunucuna kurabiliyor, posta kutularını bağlayabiliyor ve ChatGPT'nin erişebileceği işlemleri ayrı ayrı seçebiliyorsun.
>
> Okuma başlangıçta açık; gönderme ve diğer yazma işlemleri kapalı. Gönderme ve çöp kutusuna taşıma için ayrıca panel onayı kullanılabiliyor. Hesap bilgileri sunucu tarafında şifreli saklanıyor. ChatGPT'ye okuttuğun e-posta içeriği ise ChatGPT tarafından işleniyor.
>
> Standart IMAP/SMTP hesapları destekleniyor. Gmail ve Microsoft OAuth için kendi sağlayıcı uygulama kaydını ve ortam değişkenlerini yapılandırman gerekiyor; kurumsal erişim politikaları geçerli. Bu erken sürümde gerçek sağlayıcı posta kutularıyla uçtan uca doğrulama henüz tamamlanmadı.
>
> Python/FastAPI, sade HTML/CSS/JavaScript ve Upstash Redis kullanıyor. MIT lisanslı. Kurulum deneyimi, erişilebilirlik ve farklı IMAP sunucularıyla uyumluluk konusunda geri bildirim arıyorum.
>
> Kaynak kod ve kurulum: https://github.com/ozandikici/GPTmail

## General introduction — English

**Title:** GPTmail: a private email workspace with controlled ChatGPT access

> I'm building GPTmail, an open-source workspace for compatible email accounts. You deploy your own instance, connect your mailboxes, and choose which actions an AI assistant can use through its OAuth-protected MCP server.
>
> Reading starts enabled; sending and other write actions start disabled. Sending and moving mail to Trash can also require approval in the dashboard. Account credentials are encrypted on the server. Email content you ask ChatGPT to read is still processed by ChatGPT.
>
> Standard IMAP/SMTP accounts are supported. Gmail and Microsoft OAuth require your own provider app registration and deployment configuration, and provider policies still apply. This is an early single-owner project; live provider mailbox testing has not yet been completed.
>
> The stack is Python/FastAPI, HTML/CSS/JavaScript and Upstash Redis, under the MIT license. I'd welcome feedback on setup, accessibility and IMAP interoperability.
>
> Source and setup: https://github.com/ozandikici/GPTmail

Bu iki taslak genel kullanım içindir. **Hacker News veya r/opensource'a kopyalama:** aşağıdaki güncel kuralları uygulayarak kendi metnini yaz.

## Dizin katkısı için hazır taslak

**Aday:** [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers). Projenin herkese açık kaynak deposu ve kendi kurulum yolu, listenin kapsamıyla örtüşüyor; kabul kararı liste bakımcılarına ait. Liste kısa açıklama, uygun kategori, alfabetik sıra ve mevcut satır biçimini istiyor. [Katkı kuralları](https://github.com/punkpeye/awesome-mcp-servers/blob/main/CONTRIBUTING.md).

**Açıklama:**

> OAuth-protected email MCP server with a private multi-account dashboard, configurable tool permissions, and approval queues for sending and Trash actions.

**Bağlantılı satır taslağı:**

```markdown
- [ozandikici/GPTmail](https://github.com/ozandikici/GPTmail) - OAuth-protected email MCP server with a private multi-account dashboard, configurable tool permissions, and approval queues for sending and Trash actions.
```

**PR açıklaması taslağı:**

> Adds GPTmail, an MIT-licensed Python email MCP server with source-based installation instructions. It supports compatible IMAP/SMTP mailboxes and configurable Google/Microsoft OAuth. The dashboard is single-owner and password protected; each MCP capability has a separate permission, with send/Trash approval queues available. The repository documents provider setup and current testing limits. I maintain the project.

Gönderim sırasında listenin güncel kategorisini ve zorunlu simgelerini kontrol ederek satırı uyarlamak gerekir. Bu paket bir PR açmaz.

## Kanal seçimi ve yayın koşulları

| Kanal | Uygun yol | Şu anki karar |
|---|---|---|
| Kendi GitHub deposu | README, About, topics, lisans, kurulum rehberi | Ana tanıtım adresi; kaynak ve kurulum odaklı |
| Awesome MCP Servers | Kurallara uygun tek proje katkısı | Yukarıdaki taslak hazır; gönderilmedi |
| r/selfhosted | Proje üç aydan gençken yalnızca güncel **New Project Megathread**; İngilizce, açık teknik bağlam | Bağımsız tanıtım gönderisi hazırlama; önce gerçek kurulum deneyimi ve test kanıtı |
| r/opensource | OSI lisanslı repo, uygun **Promotional** etiketi, tartışmaya katılım; yapay zekâ üretimi içerik yasak | Hazır metni kullanma; kullanıcı kendi deneyimini kendi cümleleriyle yazmalı |
| Show HN | İnsanların deneyebileceği bir proje, kişisel teknik açıklama; insan tarafından yazılmış gönderi | Aşağıdaki notlardan bağımsız kişisel metin hazırlanmalı; otomatik gönderim yok |
| Awesome Selfhosted | İlk etiketli sürümün üzerinden dört aydan fazla zaman geçmeli; belirli bir bulut sağlayıcısına bağımlı yazılım kapsam dışı | Şimdilik uygun değil: Upstash'a özgü REST bağımlılığı, yeni sürüm ve LLM katkı yasağı |

Kurallar için: [r/selfhosted](https://www.reddit.com/r/selfhosted/wiki/rules/), [r/opensource](https://www.reddit.com/r/opensource/), [Show HN](https://news.ycombinator.com/showhn.html), [HN genel kuralları](https://news.ycombinator.com/newsguidelines.html), [Awesome Selfhosted katkı şartları](https://github.com/awesome-selfhosted/awesome-selfhosted-data/blob/master/CONTRIBUTING.md). Bunlar 10 Ekim 2026 kontrolüdür; paylaşım günü tekrar kontrol et.

Reddit, tekrar eden toplu tanıtımları ve istenmeyen kitlesel etkileşimi spam olarak değerlendirir. Aynı metni çok sayıda topluluğa dağıtma, otomatik DM gönderme veya oy isteme. [Reddit spam politikası](https://support.reddithelp.com/hc/en-us/articles/360043504051-Spam).

## Show HN için kişisel yazım notları

HN, üretilmiş veya yapay zekâ tarafından düzenlenmiş metin ve otomatik gönderim istemiyor. Bu nedenle burada kopyalanacak Show HN gönderisi bulunmuyor. Kullanıcı şu somut bilgileri kendi deneyimiyle ilişkilendirip kendisi yazmalı:

- Posta hesaplarını tek yerde yönetme ihtiyacı nereden doğdu?
- AI erişiminde hangi işlem ayrı izin gerektiriyor ve neden?
- Hangi kurulumu gerçekten denedin; hangi sağlayıcı henüz denenmedi?
- Sunucu tarafı şifreleme neyi koruyor, ChatGPT'ye hangi veri gidiyor?
- Denemek isteyen biri kaynak depodan nasıl kendi kurulumuna geçebilir?
- Hangi teknik konuda geri bildirim arıyorsun?

Başlık **Show HN:** önekiyle başlar; abartılı sıfatlar veya oy çağrısı içermez. Özel yönetici paneli linkini açık demo diye sunma. Deneme yolu henüz yeterince anlaşılır değilse Show HN paylaşımını ertele.

## Görseller ve doğrulanabilir iddialar

Kullanılabilecek görseller: yeni logo, boş hesap durumunu gösteren panel görüntüsü ve gerçek mail içermeyen bir bağlantı/yetki ekranı. Ekran görüntüsünde posta adresi, mesaj, token, yönetici parolası veya bulut hesap bilgisi bulunmamalı. Örnek veri kullanılırsa açıkça örnek olduğu belirtilmeli.

**Söylenebilir:** MIT lisanslı, kendi kurulabilen kaynak kod, parola korumalı tek sahip paneli, şifreli hesap kayıtları, ayrı MCP işlem yetkileri, gönderme/Trash onayları, sağlayıcı yapılandırması gerektiren OAuth.

**Söylenmemeli:** “Her sağlayıcı hazır bağlı”, “tamamen çevrimdışı”, “e-postalar hiçbir yere gitmez”, “bağımsız güvenlik denetiminden geçti”, “sınırsız ücretsiz”, “resmî ChatGPT/Gmail/Microsoft ürünü”, “herkese açık canlı demo”.

Ücretsiz planlarla kurulum, sağlayıcıların güncel kota ve kullanım koşullarına bağlıdır. Tanıtımın çağrısı **kaynak kodu incele, kendi ortamında kur, somut geri bildirim ver** olmalıdır.
