# Host CODECRAFT (v91) — วิธีเอาเว็บขึ้น host

เว็บนี้เป็น **static site ไม่มี build step** (`index.html` + `assets/`)
host ที่ไหนก็ได้ที่เสิร์ฟไฟล์ static ได้

> โค้ดใช้ **relative path** (`assets/...`, `sw.js`,
> `offline-manifest-...json`) จึงทำงานได้ทั้งแบบ root ของโดเมน
> (`example.com/`) และแบบ subfolder (`example.com/kuroya/`)
> ขอแค่เก็บโครงสร้างโฟลเดอร์ `codecraft/` ไว้ครบ ห้ามย้ายไฟล์แยกกัน

## วิธีที่ 1 — GitHub Pages จาก repo นี้ (ไม่ใช้ Vercel)

repo นี้มี workflow `.github/workflows/pages.yml` ที่ publish โฟลเดอร์
`codecraft/` ขึ้น GitHub Pages อัตโนมัติเมื่อ push

- **URL:** https://affranphanjampee-art.github.io/kuroya/
- เปิดใช้ครั้งแรก: Settings → Pages → Source เลือก **GitHub Actions**
  (ทำแล้วในรอบนี้ — ถ้า workflow ไม่รัน ให้เปิดเองที่หน้านี้)
- แก้ไฟล์ใน `codecraft/` แล้ว push → เว็บอัปเดตเอง
- หมายเหตุ: GitHub Pages ไม่รองรับ custom headers (cache/security)
  แต่เว็บทำงานได้ปกติ — headers ใน `vercel.json`/`netlify.toml`
  มีผลเฉพาะ host ที่รองรับ

## วิธีที่ 2 — Vercel (ทางเลือก)

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

## วิธีที่ 3 — Netlify

1. Netlify → **Add new site → Import from Git** → เลือก repo นี้
2. **Publish directory:** `codecraft`, **Build command:** เว้นว่าง
3. Deploy — `netlify.toml` ในโฟลเดอร์นี้ตั้ง headers ให้แล้ว

## วิธีที่ 4 — Cloudflare Pages

1. Cloudflare Pages → **Create → Pages → Connect to Git**
2. **Root directory:** `codecraft`, **Build command:** เว้นว่าง,
   **Output directory:** เว้นว่าง
3. Deploy — `_headers` ในโฟลเดอร์นี้ตั้ง headers ให้แล้ว

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
