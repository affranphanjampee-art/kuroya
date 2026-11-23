# CODECRAFT v91 — บัญชีไฟล์ (File Inventory)

> จัดทำเมื่อ 2026-11-23 จาก `CODECRAFT-v91-account-split.zip` (Google Drive)
> โฟลเดอร์นี้เป็น static site ที่ต้อง host แบบ `codecraft/` เป็น root
> ดูวิธี host ใน `../HOSTING.md`

## ทำไมไฟล์ถึงย้ายไม่ได้

เว็บนี้ใช้ **relative path** (`assets/...`, `sw.js`,
`offline-manifest-...json`) ทั้งใน `index.html`, `sw.js`,
`offline-manifest*.json` และสคริปต์ใน `assets/packed-main-v1/`
(เช่น `cc-motion-offline-v91.js` ทำ
`fetch("offline-manifest-main-account-split-v91.json")` และ
`navigator.serviceWorker.register("sw.js")`)

> เดิมใช้ absolute path (`/assets/...`) แล้วแก้เป็น relative
> เมื่อ 2026-11-23 เพื่อให้ host ได้ทั้งที่ root ของโดเมนและ
> subfolder (เช่น GitHub Pages ที่ `...github.io/kuroya/`)

ดังนั้น:

- **ห้ามย้าย/ลบ** ไฟล์ที่อยู่ในรายการด้านล่างโดยไม่แก้โค้ดที่อ้างถึง
- `sw.js` ต้องอยู่ข้าง `index.html` (scope ของ service worker)
- `offline-manifest*.json` ต้องอยู่ข้าง `index.html` เพราะโค้ด fetch แบบ relative
- การจัดระเบียบจึงทำเป็น **เอกสาร + config** ไม่ได้ย้ายไฟล์จริง

## โครงสร้างปัจจุบัน

```
codecraft/
├── index.html                  ← หน้าเว็บหลัก (CODECRAFT — ห้องเรียนเขียนโค้ด)
├── classroom-speed-test.html   ← หน้าทดสอบความพร้อมห้องเรียน (ครู/นักเรียน)
├── favicon.ico
├── favicon-graphite-v2.ico
├── sw.js                       ← service worker (ออฟไลน์/PWA)
├── robots.txt / sitemap.xml    ← SEO (ชี้ไป bisque-garden-tau.vercel.app)
├── offline-manifest.json       ← manifest พื้นฐาน (legacy)
├── offline-manifest-main-account-split-v91.json  ← manifest ปัจจุบัน (v91)
├── offline-manifest-main-*.json (89 ไฟล์)         ← manifest ประวัติแต่ละเวอร์ชัน
├── vercel.json / netlify.toml / _headers / .nojekyll  ← config สำหรับ host
├── HOSTING.md / README.md / docs/                 ← เอกสาร
└── assets/
    ├── css/            96 ไฟล์ (~1.7 MB)  สไตล์ธีม graphite + โมดูล cc-*
    ├── packed-main-v1/ 198 ไฟล์ (~5.2 MB) สคริปต์หลัก (บทเรียน/บัญชี/โปรไฟล์)
    ├── images/         29 ไฟล์ (~4.2 MB)  รูปบทเรียน + ไอคอน UI
    ├── fonts/           2 ไฟล์ (~224 KB)  Noto Sans Thai
    ├── offline/        12 ไฟล์ (~100 KB)  worker รันโค้ดออฟไลน์
    └── vendor/         21 ไฟล์ (~112 MB)  Clang + Pyodide WASM, Supabase
```

รวม **455 ไฟล์** (~124 MB เมื่อแตกไฟล์)

## ไฟล์ที่ใช้งานจริง (v91)

- `index.html` อ้างถึง **86 ไฟล์** ใน `assets/` โดยตรง (57 JS + 50 CSS
  มีซ้ำบางส่วน) — ตรวจสอบแล้ว **ครบทุกไฟล์บนดิสก์**
- `offline-manifest-main-account-split-v91.json` รายการ **163 ไฟล์**
  (core 152 + python 5 + clang 6) — ครบทุกไฟล์ (รวมไฟล์ root)
- สคริปต์ออฟไลน์ที่ใช้งาน: `assets/packed-main-v1/cc-motion-offline-v91.js`
  (fetch manifest v91 + register `/sw.js`)
- สคริปต์บัญชีที่ใช้งาน: `assets/packed-main-v1/cc-account-split-v91.js`
  (Supabase `https://nohpwvoacgggsnjkdben.supabase.co`, ใช้ publishable key)

## ไฟล์ประวัติ (เก็บไว้ ไม่ได้ใช้โดยตรงใน v91)

- `offline-manifest-main-*.json` 89 ไฟล์ — manifest ของแต่ละเวอร์ชันเก่า
  เก็บไว้เพราะ `sw.js` รายการ `OLD` อ้างถึง cache ชื่อเก่า และสคริปต์เก่า
  ใน `packed-main-v1/` ยังอ้างถึง manifest ของตัวเอง
- `assets/css/` และ `assets/packed-main-v1/` มีไฟล์หลายเวอร์ชันซ้อนกัน
  (เช่น `cc-compact-lessons-v1..v13`, `cc-compact-profile-v1..v81`)
  เฉพาะเวอร์ชันที่ `index.html` v91 โหลดเท่านั้นที่ทำงาน
- **ไฟล์ซ้ำเนื้อหาเดียวกัน** (md5 ตรงกัน):
  - `cc-first-rank-v84.css`, `cc-five-ranks-v86.css`, `cc-level-50-v87.css`,
    `cc-rank-names-v88.css`, `cc-second-rank-v85.css`, `cc-thai-ranks-v89.css`
    (6 ไฟล์ เนื้อหาเดียวกัน — v91 โหลดเฉพาะ `cc-thai-ranks-v89.css`)
  - `cc-home-motion-v1.css` = `cc-home-motion-v6.css` (v91 โหลด v6)

> ไม่ได้ลบไฟล์ซ้ำ/ประวัติออก เพราะเสี่ยงทำระบบออฟไลน์ (cache migration)
> พัง ถ้าจะลดขนาด repo ให้ย้ายไฟล์เหล่านี้ออกพร้อมแก้ `sw.js` และ
> manifest ที่อ้างถึง แล้วทดสอบโหมดออฟไลน์ใหม่ทั้งระบบ

## ไฟล์ใหญ่ (vendor — ห้ามลบ)

| ไฟล์ | ขนาด | หน้าที่ |
|---|---|---|
| `assets/vendor/clang/gen/llvm.core.wasm` | 69 MB | ตัวรัน C/C++ ในเบราว์เซอร์ |
| `assets/vendor/clang/gen/llvm-resources.tar` | 28 MB | ทรัพยากร Clang |
| `assets/vendor/pyodide/pyodide.asm.wasm` | 9.6 MB | ตัวรัน Python ในเบราว์เซอร์ |
| `assets/vendor/pyodide/python_stdlib.zip` | 2.3 MB | stdlib ของ Python |

ไฟล์เหล่านี้จำเป็นสำหรับโหมดออฟไลน์ (~120 MB) — GitHub เตือนว่าไฟล์
69 MB เกิน 50 MB ที่แนะนำ แต่ยัง push ได้ (ลิมิต 100 MB/ไฟล์)
ถ้าเวอร์ชันหน้าโตกว่านี้ให้ใช้ Git LFS
