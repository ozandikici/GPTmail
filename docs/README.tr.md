# GPTmail — Türkçe hızlı kurulum

GPTmail, IMAP posta kutularını bir web panelinden yönetebileceğin, ChatGPT için **OAuth korumalı MCP** bağlantısı sunan açık kaynak projedir. Salt okunur başlayıp göndermeyi, cevaplamayı, iletmeyi, klasör oluşturmayı, arşivlemeyi, işaretlemeyi ve çöp kutusuna taşımayı ayarlardan ayrı ayrı açabilirsin.

## Kurulum (Vercel + Upstash)

1. GitHub'da **public** `GPTmail` adlı bir repo oluştur. Git ve GitHub CLI yüklüyse önce `gh auth login` yap, ardından GPTmail klasöründen Windows PowerShell'de `./scripts/publish_github.ps1`, macOS/Linux'ta `bash scripts/publish_github.sh` çalıştır. Bu komut `ozandikici/GPTmail` deposunu oluşturur ve içeriği yükler. Alternatif olarak GitHub'da boş repoyu elle oluşturup `git init`, `git add .`, `git commit` ve `git push` kullanabilirsin.
2. [Vercel](https://vercel.com/new) üzerinde **Import Git Repository** ile projeyi içe aktar. FastAPI `app.py` dosyasından otomatik tespit edilir.
3. [Upstash Redis](https://vercel.com/marketplace/upstash) kurup Vercel projesine bağla. Redis'in REST URL ve yazma yetkili REST token bilgileri gereklidir.
4. Bilgisayarında proje klasöründe `pip install -r requirements.txt` komutunu, ardından `python scripts/make_secrets.py` komutunu çalıştır. İstediğin güçlü yönetici parolasını belirle; ekranda çıkan **ADMIN_PASSWORD_HASH** ve **DATA_ENCRYPTION_KEY** değerlerini sakla.
5. Vercel **Project Settings → Environment Variables** bölümüne `APP_BASE_URL`, `ADMIN_PASSWORD_HASH`, `DATA_ENCRYPTION_KEY`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` değerlerini ekle. `APP_BASE_URL` gerçek `https://...vercel.app` adresinin tamamı olmalı (sonunda `/` yok). Değişiklikten sonra **Redeploy** yap.
6. Siteni aç, belirlediğin yönetici parolasıyla giriş yap, **Hesaplar** kısmından IMAP ve gerekiyorsa SMTP bilgilerini gir. Uygulama bağlantıyı kontrol ederek bilgileri şifreli kaydeder.
7. **MCP Yetkileri** kısmında ChatGPT'nin ne yapacağını işaretle. Gönderme ve silme onayları başlangıçta açıktır.
8. **ChatGPT Bağlantısı** kısmındaki `https://...vercel.app/mcp` adresini ChatGPT'nin özel MCP/plugin bağlantısı ekleme bölümüne gir ve OAuth ile bağlan. Açılan GPTmail sayfasında yönetici parolanla yetki ver.

## Önemli sınırlar

- Vercel ücretsiz hesabı tek başına yetmez: **kalıcı şifreli kayıt** için Upstash gibi bir veritabanı gerekir. Ücretsiz katman limitlerini kontrol et.
- Gizli bilgiler GitHub'a **asla** yüklenmemeli. `.env` dosyası `.gitignore` kapsamındadır. Gerçek şifreni ChatGPT sohbetine de yazma.
- E-postaların içeriğini ChatGPT'ye okuttuğunda **mail metni ChatGPT tarafından işlenir**; yalnızca IMAP/SMTP giriş şifreleri ChatGPT'ye verilmez.
- Gmail / Outlook tarafında uygulama şifresi desteği olmayan veya sadece OAuth kabul eden hesaplar bu sürümde çalışmaz.
- Silme, kalıcı silme değil **Trash'a taşıma** işlemidir. Bazı eski IMAP sunucularında `MOVE` yoksa işlem güvenli biçimde reddedilir.
- İlk bağlantının çalışması için gerçek HTTPS dağıtımı ve ChatGPT hesabında özel MCP bağlantısı ekleme desteği gerekir. Yereldeki `localhost` üzerinden ChatGPT bulut bağlantısı kurulamaz.
- Gönderme isteğinde SMTP bilgisi kaydedilmiş olmalı. Yetkiler açılsa bile onay anahtarı aktifse gönderim önce panelde **Onay Bekleyenler** bölümüne düşer.

Geliştirme ve tüm API ayrıntıları için [İngilizce README](../README.md) dosyasına bakabilirsin.
