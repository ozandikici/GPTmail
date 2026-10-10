# GPTmail

**Tüm kutuların. Tek özel alanın.**

GPTmail, uyumlu posta hesaplarını tek bir parola korumalı çalışma alanından yönetebileceğin, ChatGPT için **OAuth korumalı MCP** bağlantısı sunan açık kaynak projedir. Kendi kurulumunu yapar, hesaplarını eklersin; AI asistanının hangi işlemleri yapabileceğini ayrı ayrı belirlersin.

Okuma başlangıçta açıktır. Gönderme, cevaplama, iletme, klasör oluşturma, arşivleme, işaretleme ve çöp kutusuna taşıma kapalı başlar. Gönderme ve Trash işlemlerinde ayrıca panel onayı kullanılabilir; bu iki onay anahtarı başlangıçta açıktır.

## Hangi hesaplar bağlanabilir?

| Hesap | Bağlantı yolu | Önkoşul |
|---|---|---|
| Gmail / Google Workspace | Google OAuth | Kendi Google uygulama kaydın, client bilgileri ve izin verilen hesap erişimi |
| Outlook.com / Microsoft 365 | Microsoft OAuth | Kendi Entra uygulama kaydın ve uygun IMAP/SMTP politikaları |
| iCloud, Yahoo, Zoho, özel alan adı ve diğer uyumlu servisler | IMAP/SMTP | Sağlayıcının izin verdiği erişim ve gerekiyorsa uygulama parolası |
| IMAP/SMTP sunmayan servisler | Doğrudan destek yok | Ayrı entegrasyon gerekir |

Aynı sağlayıcıdan birden çok hesap ekleyebilirsin. Her hesap ayrı bağlanır ve IMAP kontrolü başarılı olmadan kaydedilmez. Sağlayıcının planı, IMAP erişimi ve kurumsal politikaları geçerlidir; “tüm kutular” her servis için koşulsuz uyumluluk garantisi değildir.

Google/Microsoft butonları, gerekli uygulama değişkenleri tanımlandıktan sonra kullanılabilir. Kaynak depoda ortak bir sağlayıcı uygulaması veya hazır bağlı posta hesabı bulunmaz. Ayrıntılar: [Sağlayıcı OAuth kurulum rehberi](provider-oauth.md).

## Kurulum (Vercel + Upstash)

1. [Kaynak depoyu](https://github.com/ozandikici/GPTmail) kendi GitHub hesabına fork et veya kendi boş depouna yükle. Dahil edilen `scripts/publish_github.ps1` / `.sh` yardımcıları `ozandikici/GPTmail` hedefini kullanır; başka hesapta kullanacaksan hedef sahibi önce değiştirmelisin. GitHub CLI ile yayınlamak için `gh auth login` gerekir.
2. [Vercel](https://vercel.com/new) üzerinde **Import Git Repository** ile projeyi içe aktar. FastAPI `app.py` dosyasından otomatik tespit edilir.
3. [Upstash Redis](https://vercel.com/marketplace/upstash) kurup Vercel projesine bağla. Redis'in REST URL ve yazma yetkili REST token bilgileri gereklidir.
4. Bilgisayarında proje klasöründe `pip install -r requirements.txt` komutunu, ardından `python scripts/make_secrets.py` komutunu çalıştır. İstediğin güçlü yönetici parolasını belirle; ekranda çıkan **ADMIN_PASSWORD_HASH** ve **DATA_ENCRYPTION_KEY** değerlerini sakla.
5. Vercel **Project Settings → Environment Variables** bölümüne `APP_BASE_URL`, `ADMIN_PASSWORD_HASH`, `DATA_ENCRYPTION_KEY`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` değerlerini ekle. `APP_BASE_URL` gerçek `https://...vercel.app` adresinin tamamı olmalı (sonunda `/` yok). Değişiklikten sonra **Redeploy** yap.
6. Siteni aç, belirlediğin yönetici parolasıyla giriş yap. **Hesaplar** bölümünden IMAP/SMTP bilgilerini gir veya [Google/Microsoft kurulumu](provider-oauth.md) sonrasında sağlayıcının OAuth akışını tamamla. Uygulama bağlantıyı kontrol ederek hesap bilgilerini sunucu tarafında şifreli kaydeder.
7. **MCP Yetkileri** kısmında ChatGPT'nin ne yapacağını işaretle. Gönderme ve silme onayları başlangıçta açıktır.
8. **ChatGPT Bağlantısı** kısmındaki `https://...vercel.app/mcp` adresini ChatGPT'nin özel MCP/plugin bağlantısı ekleme bölümüne gir ve OAuth ile bağlan. Açılan GPTmail sayfasında yönetici parolanla yetki ver.

Google için ayrıca `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`; Microsoft için `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` ve gerekiyorsa `MICROSOFT_TENANT_ID` tanımlanır. Callback adresleri sırasıyla `/oauth/mail/google/callback` ve `/oauth/mail/microsoft/callback` yolundadır. Gerçek kurulum adresinin tamamını sağlayıcı uygulamasına kaydet. Mail sağlayıcısının OAuth bağlantısı ile ChatGPT'nin GPTmail'e verdiği OAuth bağlantısı birbirinden ayrıdır.

**`DATA_ENCRYPTION_KEY` değerini koru.** Değiştirirsen eski şifreli hesap kayıtları okunamaz. Parola veya token değerlerini README'ye, GitHub'a ya da sohbet mesajına ekleme.

## Önemli sınırlar

- Vercel ücretsiz hesabı tek başına yetmez: **kalıcı şifreli kayıt** için Upstash gibi bir veritabanı gerekir. Ücretsiz katman limitlerini kontrol et.
- Gizli bilgiler GitHub'a **asla** yüklenmemeli. `.env` dosyası `.gitignore` kapsamındadır. Gerçek şifreni ChatGPT sohbetine de yazma.
- E-postaların içeriğini ChatGPT'ye okuttuğunda **mail metni ChatGPT tarafından işlenir**; yalnızca IMAP/SMTP giriş şifreleri ChatGPT'ye verilmez.
- Gmail / Outlook OAuth kodu, sağlayıcı uygulama kaydı ve hesap sahibinin izni olmadan bağlantı kurmaz. Google test kullanıcısı/uygulama doğrulaması ve Microsoft yönetici/SMTP politikaları erişimi sınırlandırabilir.
- Silme, kalıcı silme değil **Trash'a taşıma** işlemidir. Bazı eski IMAP sunucularında `MOVE` yoksa işlem güvenli biçimde reddedilir.
- İlk bağlantının çalışması için gerçek HTTPS dağıtımı ve ChatGPT hesabında özel MCP bağlantısı ekleme desteği gerekir. Yereldeki `localhost` üzerinden ChatGPT bulut bağlantısı kurulamaz.
- Gönderme isteğinde SMTP bilgisi kaydedilmiş olmalı. Yetkiler açılsa bile onay anahtarı aktifse gönderim önce panelde **Onay Bekleyenler** bölümüne düşer.
- Tek bir güvenilir sahibi olan kişisel kurulum hedeflenir. Bağımsız güvenlik denetimi yapılmamıştır; çok kiracılı bir posta hizmeti değildir.
- Gerçek ChatGPT OAuth bağlantısı dağıtımda doğrulanmıştır. Google/Microsoft veya genel IMAP/SMTP posta kutularıyla uçtan uca canlı test henüz yapılmamıştır.

Bu proje kendi ortamına kurman içindir; ortak bir posta hizmeti veya herkese açık demo sunmaz. Projeyi denemek için kaynak depodan kendi kurulumunu yap.

Geliştirme ve tüm API ayrıntıları için [İngilizce README](../README.md) dosyasına bakabilirsin.

Projeyi yararlı bulduysan [GitHub'da yıldız vererek](https://github.com/ozandikici/GPTmail) destek olabilirsin. Kurulum deneyimini paylaşman, hata bildirmen ve katkı göndermen de gelişmesine yardımcı olur. Lütfen herkese açık bildirimlere posta içeriği, hesap bilgisi veya parola ekleme.
