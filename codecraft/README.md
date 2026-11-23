# CODECRAFT — ห้องเรียนเขียนโค้ด (v91)

เว็บหลัก CODECRAFT เวอร์ชัน **v91-account-split** — สื่อเรียนรู้การเขียนโปรแกรม
C, Python, C++, C# และ Java พร้อมแบบฝึกและแบบประเมิน

- **ไฟล์ต้นทาง:** `CODECRAFT-v91-account-split.zip` (Google Drive)
- **Drive File ID:** `1-4ViSSmovVH7sZehtIdrb3v2JiyTjo4P`
- **วันที่ไฟล์:** 2026-11-23
- **คำอธิบายใน Drive:** "CODECRAFT v91 backup: separate signup and sign-in, password visibility."
- **URL เดิม:** https://bisque-garden-tau.vercel.app/

## โครงสร้าง

- `index.html` — หน้าเว็บหลัก
- `classroom-speed-test.html` — หน้าทดสอบความเร็วห้องเรียน
- `assets/css/` — สไตล์ (ธีม graphite + โมดูล cc-*)
- `assets/packed-main-v1/` — สคริปต์หลักของเว็บ (บทเรียน, บัญชี, โปรไฟล์ ฯลฯ)
- `assets/images/`, `assets/fonts/` — รูปภาพและฟอนต์
- `assets/offline/`, `assets/vendor/` — ตัวรันโค้ดออฟไลน์ (Clang / Pyodide WASM)
- `offline-manifest*.json`, `sw.js` — manifest สำหรับโหมดออฟไลน์ / PWA

รวม 454 ไฟล์ (~124 MB เมื่อแตกไฟล์ โดย ~112 MB เป็น vendor WASM สำหรับรันโค้ดในเบราว์เซอร์)

## วิธีรัน (ดูตัวอย่าง)

```bash
cd codecraft
python3 -m http.server 8000
# เปิด http://localhost:8000/
```

> โฟลเดอร์นี้อยู่แยกจากแอป Anime Notebook (Streamlit) ที่ root ของ repo
> (`app.py`) ไม่ได้ทับกัน
