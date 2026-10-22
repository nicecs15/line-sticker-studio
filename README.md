# LINE Sticker Studio

Skill สำหรับ Codex (และ Claude Code) ที่ทำสติกเกอร์ LINE ได้ทั้งชุด ติดตั้งแล้วคุยเป็นภาษาไทยได้เลย
AI จะออกแบบตัวละคร คิดคำพูด วาดภาพ และทำไฟล์ zip พร้อมอัปโหลดขึ้น LINE Creators Market ให้

- **ไม่มีค่าใช้จ่ายเพิ่ม** ภาพทำผ่าน [Codex CLI](https://github.com/openai/codex) และใช้โควตาจากแพ็กเกจ ChatGPT ที่คุณมีอยู่แล้ว ไม่ต้องมี API key
- **คำไทยสะกดถูกทุกตัว** AI วาดเฉพาะภาพที่ไม่มีตัวอักษร แล้วโปรแกรมพิมพ์คำพูดด้วยฟอนต์ไทยจริงให้ สระและวรรณยุกต์จึงอยู่ถูกตำแหน่ง
  ถ้าอยากแก้คำพูดก็แค่ build ใหม่ ไม่ต้องทำภาพใหม่
- **ตรวจตามกติกา LINE ให้** ทั้งขนาดภาพ พื้นใส จำนวนภาพ ขนาดไฟล์ main/tab และความยาวชื่อกับคำอธิบายหน้าขาย
- รองรับทั้ง **บิ๊กสติกเกอร์** (396×660) และ **สติกเกอร์ปกติ** (370×320)

## สิ่งที่ต้องมี

| | |
|---|---|
| Python 3.9 ขึ้นไป | https://www.python.org/downloads/ (Windows: ติ๊ก "Add python.exe to PATH" ตอนติดตั้ง) |
| Node.js 18 ขึ้นไป | https://nodejs.org/ (ใช้ติดตั้ง Codex CLI) |
| แพ็กเกจ ChatGPT ที่ใช้ Codex ได้ | ภาพละประมาณ 2 นาที และหักจากโควตาทำภาพของแพ็กเกจ |

## ติดตั้ง

**1. ติดตั้ง Codex CLI แล้วล็อกอินด้วยบัญชี ChatGPT**

```bash
npm install -g @openai/codex
codex login
```

**2. ติดตั้ง skill** โดยเปิด `codex` แล้วพิมพ์

```
ติดตั้ง skill จาก https://github.com/nicecs15/line-sticker-studio/tree/main/skills/line-sticker
```

Codex จะใช้ skill-installer ที่มีอยู่ในตัวดาวน์โหลดให้ ระหว่างนั้นจะขออนุญาตใช้อินเทอร์เน็ต ให้กดอนุญาต
เสร็จแล้วปิด Codex แล้วเปิดใหม่

<details>
<summary>ติดตั้งเองโดยไม่ผ่าน Codex หรือใช้กับ Claude Code</summary>

ดาวน์โหลด repo นี้ (Code → Download ZIP) แล้วก๊อปโฟลเดอร์ `skills/line-sticker` ไปไว้ที่

- Codex: `~/.codex/skills/line-sticker` (Windows: `C:\Users\<ชื่อคุณ>\.codex\skills\line-sticker`)
- Claude Code: `~/.claude/skills/line-sticker`

</details>

## วิธีใช้

สร้างโฟลเดอร์สำหรับเก็บงาน เปิด Codex ในโฟลเดอร์นั้น แล้วบอกว่าอยากได้สติกเกอร์แบบไหน

```bash
mkdir my-stickers
cd my-stickers
codex
```

```
ทำสติกเกอร์แมวนักบัญชี 16 ภาพ พูดครับ ใช้คุยกับทีมในออฟฟิศ
```

Codex จะทำงานตามลำดับนี้
1. ครั้งแรกที่ใช้ จะตรวจเครื่องและติดตั้งแพ็กเกจ Python ที่ขาดให้ (ขออนุญาตก่อน)
2. ออกแบบตัวละครและร่างคำพูดทั้งชุดลง `themes/<id>/theme.yaml` แล้วให้คุณตรวจก่อนทำภาพ
3. ทำภาพ 01 เป็นภาพอ้างอิงตัวละคร เพื่อให้คุณดูว่าชอบหน้าตาไหม
4. ทำภาพที่เหลือให้หน้าตาเหมือนภาพอ้างอิง
   ตอนนี้ Codex จะขออนุญาตรันคำสั่ง `generate` นอก sandbox เพราะต้องใช้อินเทอร์เน็ต ให้กดอนุญาต
5. build แล้วตรวจ `preview.png` ทั้งชุด ภาพไหนไม่ดีจะทำใหม่ให้
6. บอกที่อยู่ไฟล์ zip และข้อความสำหรับกรอกหน้าขาย

งานทั้งหมดจะอยู่ใน `my-stickers/themes/` ส่วนโฟลเดอร์ skill มีแค่โปรแกรม
ถ้าอยากแก้คำพูดหรือทำภาพไหนใหม่ ก็พิมพ์บอก Codex ในโฟลเดอร์เดิมได้เลย

## ผลลัพธ์ใน `themes/<id>/dist/`

| ไฟล์ | ใช้ทำอะไร |
|---|---|
| `<id>-line.zip` | ไฟล์ที่อัปโหลดขึ้น [LINE Creators Market](https://creator.line.me/) (มี main.png, tab.png, 01.png..) |
| `preview.png` | ภาพรวมทั้งชุด ไว้ตรวจว่าตัวละครเหมือนกันทุกภาพ |
| `line_info.txt` | ชื่อ คำอธิบาย และ copyright ภาษาอังกฤษ/ไทย ไว้ก๊อปไปกรอกหน้าขาย |
| `upload_type.txt` | บอกว่าต้องเลือกประเภท "สติกเกอร์" หรือ "บิ๊กสติกเกอร์" ตอนสร้างรายการ |

## สั่งเองโดยไม่ผ่าน AI

โปรแกรมอยู่ในโฟลเดอร์ skill ให้รันจากโฟลเดอร์งานของคุณ

```bash
# macOS / Linux
ST=~/.codex/skills/line-sticker/sticker.py
python3 $ST doctor
```

```powershell
# Windows PowerShell
$ST = "$HOME\.codex\skills\line-sticker\sticker.py"
python $ST doctor
```

| คำสั่ง (`python $ST <คำสั่ง>`) | ทำอะไร |
|---|---|
| `doctor` | ตรวจ Python แพ็กเกจ ฟอนต์ และการล็อกอิน Codex แล้วบอกวิธีแก้ |
| `new <id> [--count N] [--regular]` | สร้างชุดใหม่จากแม่แบบ (ค่าเริ่มต้นคือบิ๊กสติกเกอร์ 16 ภาพ) |
| `list` | ดูทุกชุดพร้อมความคืบหน้า |
| `prompts <id>` | สร้าง `prompts.md` จาก theme.yaml |
| `check <id> [--all-themes]` | ตรวจคำพูด ท่าทาง และภาพที่ซ้ำกันภายในชุด (`--all-themes` เทียบกับทุกชุดที่เคยทำด้วย) |
| `generate <id> [--only 3-5] [--force] [--dry-run]` | ทำภาพที่ยังขาดผ่าน Codex CLI |
| `generate <id> --via openai` | ทำภาพผ่าน OpenAI API แทน (ต้องมี `OPENAI_API_KEY` และเสียเงินต่อภาพ) |
| `import <id> [--as NN file.png]` | นำภาพจาก `inbox/` เข้าชุด และลบพื้นขาวหรือลายตารางให้อัตโนมัติ |
| `reference <id> NN` | ตั้งภาพ NN เป็นภาพอ้างอิงตัวละคร |
| `compose <id> [--only N]` | พิมพ์คำพูดลงภาพเพื่อดูตัวอย่างก่อน build |
| `build <id>` | ทำ zip, preview และไฟล์ข้อมูลหน้าขาย |

ถ้าอยากลองเร็วๆ ให้ก๊อป `examples/cat-accountant` จากโฟลเดอร์ skill มาไว้ใน `themes/` แล้วรัน `generate cat-accountant` และ `build cat-accountant`

### ไม่มี Codex CLI: ก๊อป prompt ไปวางใน ChatGPT เอง
1. รัน `prompts <id>` แล้วเปิด `themes/<id>/prompts.md`
2. ก๊อป prompt ไปวางใน ChatGPT ทีละภาพ แล้วแนบ `reference.png` ไปด้วยตั้งแต่ภาพที่ 2 เป็นต้นไป
3. บันทึกภาพไว้ใน `themes/<id>/inbox/` ถ้าตั้งชื่อไฟล์เป็น `05.png` ภาพจะเข้าช่องที่ 5 พอดี
4. รัน `import <id>` แล้วตามด้วย `build <id>`

## ปรับแต่งตัวอักษร

ตั้งค่าในส่วน `lettering:` ของ theme.yaml หรือบอก Codex ให้เปลี่ยนให้

```yaml
lettering:
  font: Kanit-ExtraBold        # Kanit-ExtraBold (หนา อ่านง่าย), Mitr-Bold (มน), Itim-Regular (ลายมือ), Sriracha-Regular (ลายมือ)
  position: top                # ให้คำพูดอยู่เหนือตัวละคร (top) หรือใต้ตัวละคร (bottom)
  colors: ["#E8590C", "#2E86DE"]   # สีตัวอักษร วนใช้ไปตามเลขภาพ
  outline: "#2B2B35"           # สีขอบตัวอักษร
```

- ขึ้นบรรทัดใหม่ในคำพูดด้วย `\n` เช่น `text: "ขอบคุณ\nมากครับ"`
- กำหนดสีเฉพาะภาพได้ด้วย `color: "#FF0000"` ในสติกเกอร์ภาพนั้น
- ใช้ฟอนต์อื่นได้โดยวางไฟล์ `.ttf` ไว้ในโฟลเดอร์ `fonts/` ของ skill แล้วใส่ชื่อไฟล์ (ไม่ต้องมีนามสกุล) ควรเลือกฟอนต์ที่อนุญาตให้ใช้เชิงพาณิชย์

## ข้อควรรู้ก่อนขาย

- ตรวจ [แนวทางของ LINE Creators Market](https://creator.line.me/th/guideline/) ล่าสุดก่อนส่ง โดยเฉพาะเรื่องภาพที่สร้างด้วย AI
- ออกแบบตัวละครของตัวเอง อย่าเลียนแบบตัวการ์ตูนหรือแบรนด์ที่มีลิขสิทธิ์
- โควตาทำภาพของ ChatGPT มีจำกัดต่อช่วงเวลา ถ้าชนลิมิตให้รอแล้วสั่งทำต่อ ระบบจะทำต่อจากภาพที่ยังขาด

## อัปเดตเวอร์ชัน

ลบโฟลเดอร์ `~/.codex/skills/line-sticker` แล้วติดตั้ง skill ใหม่ตามขั้นที่ 2
งานใน `my-stickers/themes/` อยู่นอกโฟลเดอร์ skill จึงไม่หาย

## สำหรับนักพัฒนา

```bash
git clone https://github.com/nicecs15/line-sticker-studio.git
cd line-sticker-studio
pip install -r skills/line-sticker/requirements.txt pytest
python -m pytest -q tests
```

โค้ดทั้งหมดอยู่ใน `skills/line-sticker/` ดูโครงสร้างได้ที่ `AGENTS.md`

## License

โค้ดใช้สัญญาอนุญาต MIT (ดู `LICENSE`) ส่วนฟอนต์ใน `skills/line-sticker/fonts/` ใช้ SIL Open Font License (ดูไฟล์ `OFL-*.txt`)
