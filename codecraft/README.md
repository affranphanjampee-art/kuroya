# CODECRAFT — ห้องเรียนเขียนโค้ด (v91)

เว็บหลัก CODECRAFT เวอร์ชัน **v91-account-split** — สื่อเรียนรู้การเขียนโปรแกรม
C, Python, C++, C# และ Java พร้อมแบบฝึกและแบบประเมิน

- **ไฟล์ต้นทาง:** `CODECRAFT-v91-account-split.zip` (Google Drive)
- **Drive File ID:** `1-4ViSSmovVH7sZehtIdrb3v2JiyTjo4P`
- **วันที่ไฟล์:** 2026-11-23
- **คำอธิบายใน Drive:** "CODECRAFT v91 backup: separate signup and sign-in, password visibility."
- **URL เดิม:** https://bisque-garden-tau.vercel.app/

## เอกสาร

- **[HOSTING.md](HOSTING.md)** — วิธีเอาเว็บขึ้น host (Vercel / Netlify /
  Cloudflare Pages / GitHub Pages / รันเอง)
- **[docs/FILE-INVENTORY.md](docs/FILE-INVENTORY.md)** — บัญชีไฟล์:
  ไฟล์ที่ใช้งานจริง, ไฟล์ประวัติ, ไฟล์ซ้ำ, ไฟล์ vendor ใหญ่

## โครงสร้าง

- `index.html` — หน้าเว็บหลัก
- `classroom-speed-test.html` — หน้าทดสอบความพร้อมห้องเรียน
- `sw.js` — service worker (ออฟไลน์/PWA)
- `offline-manifest-main-account-split-v91.json` — manifest ปัจจุบัน (v91)
- `offline-manifest-main-*.json` — manifest ประวัติแต่ละเวอร์ชัน (ห้ามย้าย/ลบ
  ดูเหตุผลใน FILE-INVENTORY)
- `assets/css/` — สไตล์ (ธีม graphite + โมดูล cc-*)
- `assets/packed-main-v1/` — สคริปต์หลักของเว็บ (บทเรียน, บัญชี, โปรไฟล์ ฯลฯ)
- `assets/images/`, `assets/fonts/` — รูปภาพและฟอนต์
- `assets/offline/`, `assets/vendor/` — ตัวรันโค้ดออฟไลน์ (Clang / Pyodide WASM)
- `vercel.json` / `netlify.toml` / `_headers` / `.nojekyll` — config สำหรับ host

รวม 455 ไฟล์ (~124 MB เมื่อแตกไฟล์ โดย ~112 MB เป็น vendor WASM สำหรับรันโค้ดในเบราว์เซอร์)

> ⚠️ เว็บนี้ใช้ relative path — host ได้ทั้ง root และ subfolder
> (เช่น GitHub Pages ที่ `...github.io/kuroya/`) แต่ห้ามย้ายไฟล์
> แยกจากโครงสร้าง `codecraft/` โดยไม่แก้โค้ด

## วิธีรัน (ดูตัวอย่าง)

```bash
cd codecraft
python3 -m http.server 8000
# เปิด http://localhost:8000/
```

> โฟลเดอร์นี้อยู่แยกจากแอป Anime Notebook (Streamlit) ที่ root ของ repo
> (`app.py`) ไม่ได้ทับกัน
