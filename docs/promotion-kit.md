# GPTmail — tanıtım paketi / promotion kit

Hazırlanma ve kaynak kontrol tarihi: **10 Ekim 2026**. Bu paket, GitHub kaynak kodunu gerçek açık kaynak ve geliştirici forumlarında tanıtmak için hazırlanmıştır. MCP katalog ve dizinlerine başvuru bu planın dışındadır. Yayın durumu ayrıca doğrulanan paylaşım bağlantılarıyla raporlanır; burada bir taslağın bulunması yayımlandığı anlamına gelmez.

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

## Seçilen forum: r/github proje paylaşım başlığı

[Promote your projects here — Self-Promotion Megathread](https://www.reddit.com/r/github/comments/1jy8rea/promote_your_projects_here_selfpromotion/), 10 Ekim 2026 kontrolünde sabitlenmiş, kilitsiz ve yorumlara açıktır. Başlık kısa proje açıklaması ve GitHub repo bağlantısı ister; teknik yapı ve katılım bağlamı da eklenebilir. Tanıtım için bu başlığa tek İngilizce yorum yazılır; ayrı gönderi açılmaz.

[Güncel topluluk kuralları](https://www.reddit.com/r/github/about/rules.json) düşük çabalı, yalnızca bağlantı içeren içerikleri ve spam'i yasaklar; görünür kurallarda AI içeriğine özel bir yasak yoktur. [Reddit'in AI içerik politikası](https://support.reddithelp.com/hc/en-us/articles/41180423371156-Manipulated-Content-and-Misleading-Behavior) AI kullanımının açıklanmasını ister. Paylaşım öncesinde başlığın güncel durumunu, hesabın yorum yetkisini ve aynı proje için mevcut yorum olup olmadığını kontrol et. Moderasyon kabulü veya görünürlük garantisi yoktur.

**İngilizce yorum taslağı:**

> I maintain GPTmail, an MIT-licensed Python project for managing multiple email accounts through a private dashboard and MCP.
>
> It supports compatible IMAP/SMTP accounts, per-tool permissions, and approval queues for sending messages and moving them to Trash. Google and Microsoft OAuth integrations require your own provider app registrations. This is an early release; live provider mailbox testing is still incomplete.
>
> Source, screenshots, and setup instructions: https://github.com/ozandikici/GPTmail
>
> You deploy your own instance and keep mailbox credentials in your deployment. Feedback on setup documentation and provider compatibility would help improve the project.
>
> Disclosure: AI tools helped develop the project and draft this comment.

**İsteğe bağlı GitHub star çağrısı:**

> If the project is useful to you, a GitHub star is welcome.

Bu cümle yalnızca GitHub deposuna yöneliktir; Reddit oyu, karşılıklı star veya ödül karşılığı etkileşim istenmez. Paylaşımdaki tek ürün bağlantısı kaynak deposudur; özel panel ya da çalışan sunucu adresi eklenmez.

## Kanal seçimi ve yayın koşulları

| Kanal | Uygun yol | Şu anki karar |
|---|---|---|
| Kendi GitHub deposu | README, About, topics, lisans, kurulum rehberi | Ana tanıtım adresi; kaynak ve kurulum odaklı |
| r/github | Sabitlenmiş **Self-Promotion Megathread** içinde kısa açıklama, kaynak bağlantısı ve AI açıklaması | Seçilen kanal; yukarıdaki İngilizce yorum taslağı kullanılır |
| r/selfhosted | Proje üç aydan gençken yalnızca güncel **New Project Megathread**; İngilizce, açık teknik bağlam | Bağımsız tanıtım gönderisi hazırlama; önce gerçek kurulum deneyimi ve test kanıtı |
| r/opensource | OSI lisanslı repo, uygun **Promotional** etiketi, tartışmaya katılım; yapay zekâ üretimi içerik yasak | Hazır metni kullanma; kullanıcı kendi deneyimini kendi cümleleriyle yazmalı |
| Show HN | İnsanların deneyebileceği bir proje, kişisel teknik açıklama; insan tarafından yazılmış gönderi | Aşağıdaki notlardan bağımsız kişisel metin hazırlanmalı; otomatik gönderim yok |

Kurallar için: [r/github](https://www.reddit.com/r/github/about/rules.json), [r/selfhosted](https://www.reddit.com/r/selfhosted/wiki/rules/), [r/opensource](https://www.reddit.com/r/opensource/), [Show HN](https://news.ycombinator.com/showhn.html), [HN genel kuralları](https://news.ycombinator.com/newsguidelines.html). Bunlar 10 Ekim 2026 kontrolüdür; paylaşım günü tekrar kontrol et.

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

Ücretsiz planlarla kurulum, sağlayıcıların güncel kota ve kullanım koşullarına bağlıdır. Tanıtımın çağrısı **kaynak kodu incele, kendi ortamında kur, somut geri bildirim ver** olmalıdır. Platformun kuralları uygunsa **yararlı bulursan GitHub'da star ver** çağrısı eklenebilir; star sayısı veya büyüme garantisi verilmez.
