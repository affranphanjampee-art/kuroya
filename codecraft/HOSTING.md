# Host CODECRAFT (v91) — วิธีเอาเว็บขึ้น host

เว็บนี้เป็น **static site ไม่มี build step** (`index.html` + `assets/`)
host ที่ไหนก็ได้ที่เสิร์ฟไฟล์ static ได้ แต่มีเงื่อนไขสำคัญ 1 ข้อ:

> **ต้อง host แบบโฟลเดอร์ `codecraft/` เป็น root ของโดเมน**
> (`/` = `codecraft/index.html`) เพราะโค้ดใช้ absolute path
> (`/assets/...`, `/sw.js`, `/offline-manifest-...json`)
> ถ้า host ใน subfolder เช่น `example.com/codecraft/` ระบบออฟไลน์จะพัง

## วิธีที่ 1 — Vercel (แนะนำ, เว็บเดิมอยู่ที่นี่)

เว็บเดิม `bisque-garden-tau.vercel.app` อยู่บน Vercel โปรเจกต์
`bisque-garden` อยู่แล้ว (build ด้วย `python3 fetch.py` → `dist/`)
ไฟล์ใน Git นี้เป็น snapshot แบบ static — host แยกได้ดังนี้:

1. เปิด Vercel → **Add New → Project** → เลือก repo `affranphanjampee-art/kuroya`
2. ตั้งค่า:
   - **Root Directory:** `codecraft`
   - **Framework Preset:** `Other`
   - **Build Command:** เว้นว่าง (ไม่มี build)
   - **Output Directory:** เว้นว่าง (ใช้ root ที่เลือก)
3. Deploy → ได้ URL แบบ `codecraft-xxx.vercel.app`
4. (ถ้าต้องการ) เพิ่ม custom domain ใน Project → Domains

ไฟล์ `vercel.json` ในโฟลเดอร์นี้ตั้ง cache + security headers ให้แล้ว
(`index.html`/`sw.js`/manifest = ไม่ cache, `assets/` = cache 1 วัน)

## วิธีที่ 2 — Netlify

1. Netlify → **Add new site → Import from Git** → เลือก repo นี้
2. **Publish directory:** `codecraft`, **Build command:** เว้นว่าง
3. Deploy — `netlify.toml` ในโฟลเดอร์นี้ตั้ง headers ให้แล้ว

## วิธีที่ 3 — Cloudflare Pages

1. Cloudflare Pages → **Create → Pages → Connect to Git**
2. **Root directory:** `codecraft`, **Build command:** เว้นว่าง,
   **Output directory:** เว้นว่าง
3. Deploy — `_headers` ในโฟลเดอร์นี้ตั้ง headers ให้แล้ว

## วิธีที่ 4 — GitHub Pages

GitHub Pages เสิร์ฟจาก repo root ไม่ได้เสิร์ฟเฉพาะ subfolder เป็น root
ของโดเมนโดยตรง ถ้าจะใช้ต้องย้ายไฟล์ `codecraft/*` ไป repo ใหม่
(หรือ branch `gh-pages`) ให้ `index.html` อยู่ root ของ repo นั้น
ไฟล์ `.nojekyll` ในโฟลเดอร์นี้ทำให้ไฟล์ `_headers` ถูกเสิร์ฟได้

## วิธีที่ 5 — รันเอง (ทดสอบ/ห้องเรียน)

```bash
cd codecraft
python3 -m http.server 8000 --bind 0.0.0.0
# เปิด http://localhost:8000/
```

## ข้อควรระวัง

- **WASM MIME:** Vercel/Netlify/Cloudflare เสิร์ฟ `.wasm` เป็น
  `application/wasm` ให้อัตโนมัติ ไม่ต้องตั้งค่าเพิ่ม
- **COOP/COEP:** ไม่ได้ตั้งไว้โดยตั้งใจ — การเปิด COEP จะบล็อก
  Supabase cross-origin (`nohpwvoacgggsnjkdben.supabase.co`) ที่เว็บใช้
  สำหรับบัญชีผู้ใช้
- **Supabase:** เว็บคุยกับ Supabase โดยตรงจากเบราว์เซอร์
  (publishable key ใน `cc-account-split-v91.js`) — ต้องเปิดเน็ต
  ครั้งแรกเพื่อเข้าสู่ระบบ/ซิงก์ข้อมูล
- **ออฟไลน์:** ครั้งแรกที่เปิดต้องโหลด ~120 MB (Clang + Pyodide)
  เพื่อเตรียมโหมดออฟไลน์ — ต้องมีพื้นที่ว่างในเบราว์เซอร์พอ
- **SEO:** `robots.txt`/`sitemap.xml`/`og:url` ยังชี้ไป
  `bisque-garden-tau.vercel.app` — หลัง host ที่โดเมนใหม่ให้แก้
  3 ไฟล์นี้เป็นโดเมนใหม่
- **ขนาด repo:** ~124 MB (vendor WASM 112 MB) — GitHub เตือนไฟล์
  69 MB เกิน 50 MB ที่แนะนำ แต่ push ได้ ถ้าโตกว่านี้ใช้ Git LFS
