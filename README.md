# Professional Telegram PDF Converter Bot

Production-ready, asynchronous Telegram bot built with Aiogram 3, Pillow, ReportLab, pypdf, LibreOffice Headless, PostgreSQL, Redis, and RQ.

## Quick start
With Node.js, Docker Desktop, and a bot token in `.env`, run:

    npm run dev

This starts Docker Desktop if needed, builds the bot, and starts PostgreSQL,
Redis and the conversion workers. Press Ctrl+C to stop the stack.

## Running Automated Tests
    pytest -v
## Serverga joylash (Linux, PostgreSQL, GitHub)

Server uchun Docker Engine, Compose v2, Git, Bash va flock kerak. Quyidagi misol bitta bot va ikkita konvertatsiya workerini ishga tushiradi. Linux yadrosi Landlock va seccomp’ni qo‘llashi kerak. Serverda alohida deploy foydalanuvchisini yarating va Docker’ni boshqarish huquqini faqat ishonchli hisobga bering.

1. O‘z GitHub repozitoriyingizni serverga aynan `/opt/pdfbot` manziliga klonlang. Deploy foydalanuvchisi shu papkaga yoza olsin. Private repo uchun serverga faqat o‘qish huquqli GitHub deploy key bering. Avvaldan ishlayotgan Compose loyihasini ko‘chirsangiz, oldingi project nomini `COMPOSE_PROJECT_NAME` bilan saqlang: boshqa nom boshqa volume yaratadi.
2. `cd /opt/pdfbot && cp .env.example .env && chmod 600 .env`. `BOT_TOKEN`ga BotFather tokenini, `ADMIN_IDS`ga o‘zingizning **raqamli Telegram ID**ingizni va `POSTGRES_PASSWORD`ga `openssl rand -hex 32` bergan qiymatni yozing. Compose serverdagi DB manzilini o‘zi o‘rnatadi. Tokenni GitHub’ga qo‘ymang.
3. Xuddi shu tokenli eski polling jarayonini to‘xtating. Deploy foydalanuvchisi nomidan `bash deploy/update.sh` bajaring. Skript image yig‘adi, bazani zaxiralaydi, servislar holatini va haqiqiy Office konvertatsiyasini tekshiradi. `docker compose ps` bilan natijani ko‘ring.
4. Telegram’da boshqa hisobdan botga fayl yoki xabar yuboring. Admin hisobining **shaxsiy chatida** `/users` orqali ID, ism, username, ro‘yxatdan o‘tish va oxirgi faollik vaqtlarini ko‘ring; keyingi sahifa uchun `/users 2`. `/admin` umumiy statistikani ko‘rsatadi. Faqat yangilanish yuborgan foydalanuvchilar qayd etiladi.
5. PostgreSQL yozuvlari `postgres_data` volume’da qoladi. Yangilashda `docker compose down -v` ishlatmang. Har deploy oldidan `~/pdfbot-backups/`ga PostgreSQL dump yoziladi. Server diski ishdan chiqishiga qarshi bu papkani yopiq tashqi backupga nusxalang va tiklashni alohida test bazasida tekshiring.

### Lokal sinovdagi foydalanuvchilarni ham ko‘chirish

Avvalgi repodan yangilashdan **oldin** mavjud `bot_local.db` faylini repo tashqarisida nusxalang. Agar eski bot SQLite ishlatayotgan bo‘lsa, nusxa olishdan avval uni to‘xtating. Faylni GitHub orqali tarqatmasdan serverga xavfsiz ko‘chiring. Masalan, faqat deploy foydalanuvchisi o‘qiy oladigan `$HOME/bot_local.db` fayli uchun:

```bash
cd /opt/pdfbot
docker compose exec -T bot sh -c 'umask 077; cat > /tmp/import-users.db' < "$HOME/bot_local.db"
docker compose exec -T bot python -m app.database.import_users /tmp/import-users.db
docker compose exec -T bot rm -f /tmp/import-users.db
```

Import profil va ro‘yxatdan o‘tish vaqtini saqlaydi. Serverda allaqachon bor profil qayta yozilmaydi. Eski bazada oxirgi faollik vaqti yo‘q: u foydalanuvchi qayta murojaat qilganda to‘ladi. Agar lokal bot Docker PostgreSQL bilan ishlagan bo‘lsa, uning ma’lumotlari SQLite’da emas. Bunday holda eski serverda `docker compose exec -T postgres pg_dump -U pdfuser -Fc pdfbot > bot.dump` qiling; yangi, bo‘sh PostgreSQL bazasiga **bot ishga tushishidan oldin** `docker compose exec -T postgres pg_restore -U pdfuser -d pdfbot --exit-on-error < bot.dump` bilan tiklang. Birinchi ishga tushishda qo‘shimcha jadvallar yaratiladi.

### GitHub orqali avtomatik yangilash

- Dastlab bu o‘zgarishlarni o‘z GitHub repozitoriyingizning `main` branchiga yuboring. Oldin GitHub’ga yuborilgan baza va parol eski commitlarda qolishi mumkin. Ulashilgan repo tarixini tozalashni hamkorlar bilan kelishing; eski production parolini almashtiring.
- GitHub Actions uchun alohida SSH kalit juftligini yarating. Public key’ni serverdagi deploy foydalanuvchisining `~/.ssh/authorized_keys` fayliga qo‘shing. GitHub’da **Settings → Environments → production** ichida `SERVER_HOST`, `SERVER_USER`, `SERVER_SSH_KEY` (private key), `SERVER_KNOWN_HOSTS` (serverning mustaqil tekshirilgan SSH host-key qatori) secretlarini kiriting. Standart SSH port 22 ishlatiladi.
- **Settings → Secrets and variables → Actions → Variables** da **repository variable** `DEPLOY_ENABLED=true` qo‘ying. `main`ga yozish va production secretlarini boshqarish huquqini cheklang. Pull request testlari serverga ulanmaydi.
- Keyingi `main` pushida test, Docker build va namunaviy PDF konvertatsiyasi o‘tganidan keyin GitHub Actions serverni SSH orqali yangilaydi. Birinchi sozlashdan keyin **Actions → Test and deploy → Run workflow** bilan tekshirish mumkin. Oldingi versiyaga qaytish uchun o‘zgarishni GitHub’da revert qiling; yangi commit ham testlardan o‘tib deploy qilinadi. Baza sxemasining buzuvchi o‘zgarishlari uchun alohida migratsiya va tiklash rejasi talab qilinadi.
