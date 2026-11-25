from PIL import Image,ImageDraw,ImageFilter,ImageOps
import freetype, uharfbuzz as hb, os
from pathlib import Path
R=str(Path(__file__).resolve().parents[2]); OUT=os.environ.get('RENDER_DIR', '/tmp/kuroya-render'); os.makedirs(OUT,exist_ok=True); W,H=1280,720
path=R+'/assets/fonts/NotoSansThai.ttf'; data=open(path,'rb').read(); face=freetype.Face(path); hface=hb.Face(data)
mono='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
from PIL import ImageFont

def text(im, xy, s, size=26, color='#edf5ff'):
    # HarfBuzz shapes Thai combining marks before FreeType rasterization.
    face.set_pixel_sizes(0,size); hf=hb.Font(hface); hf.scale=(size*64,size*64)
    buf=hb.Buffer();buf.add_str(s);buf.guess_segment_properties();hb.shape(hf,buf)
    x=xy[0]*64; baseline=(xy[1]+size)*64
    for info,pos in zip(buf.glyph_infos,buf.glyph_positions):
        face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER)
        b=face.glyph.bitmap
        if b.width and b.rows:
            mask=Image.frombytes('L',(b.width,b.rows),bytes(b.buffer))
            im.paste(color,(round((x+pos.x_offset)/64)+face.glyph.bitmap_left,round((baseline-pos.y_offset)/64)-face.glyph.bitmap_top),mask)
        x+=pos.x_advance
    return x/64

def rr(d,rect,fill,outline=None,r=18,width=2):d.rounded_rectangle(rect,r,fill=fill,outline=outline,width=width)
def bg(name):
 im=ImageOps.fit(Image.open(R+'/assets/img/'+name+'.jpg').convert('RGB'),(W,H)).convert('RGBA')
 im=Image.alpha_composite(im,Image.new('RGBA',(W,H),(3,8,23,205))).convert('RGB')
 return im

def base(n,title,bgname,oc):
 im=bg(bgname);d=ImageDraw.Draw(im)
 d.rectangle((0,0,W,8),fill='#32d5eb');rr(d,(36,28,88,80),'#28c8df',r=12)
 text(im,(51,32),'C',30,'#061321');text(im,(105,29),'CODECRAFT',25,'#f5faff'); text(im,(105,60),'LEARN  •  PRACTICE  •  BUILD',13,'#9ab1d8')
 rr(d,(1048,36,1235,72),'#16223d','#375477',r=16);text(im,(1070,38),f'บทที่ 1  •  {n:02d} / 08',17,'#9beafd')
 text(im,(42,105),title,35,'#ffffff');d.line((42,162,840,162), fill='#319ab9',width=2)
 rr(d,(41,186,840,665),'#101b31','#334969',r=20)
 # The animated character is composited during video encoding.
 # Keep a subtle backdrop behind the transparent cut-out.
 rr(d,(877,187,1237,665),'#172340','#45537d',r=22)
 d.ellipse((900,225,1215,540),fill='#202f54')
 return im

def box(im,rect,fill='#1c2b45',outline='#39516e'):rr(ImageDraw.Draw(im),rect,fill,outline,r=13)
def txt(im,x,y,s,size=25,c='#edf5ff'):text(im,(x,y),s,size,c)
def mono_text(im,x,y,s,size=20,c='#dce9ff'):
 ImageDraw.Draw(im).text((x,y),s,font=ImageFont.truetype(mono,size),fill=c,spacing=5)

def make(n,count=None):
 titles=['เปิดบทเรียน','ตัวแปรคืออะไร?','ชนิดข้อมูลในภาษา C','การประกาศตัวแปร','ตัวอย่างโปรแกรมภาษา C','ลองทดสอบความเข้าใจ','เฉลยและสรุปบทเรียน','จบบทเรียน']
 bgs=['bg-intro','bg-concept','bg-concept','bg-concept','bg-code','bg-concept','bg-finale','bg-intro']
 oc=['oc-1','oc-1','oc-2','oc-1','oc-2','oc-1','oc-2','oc-1']
 im=base(n,titles[n-1],bgs[n-1],oc[n-1]);d=ImageDraw.Draw(im)
 if n==1 or n==8:
  txt(im,115,250,'CODECRAFT',75,'#67e8f9');txt(im,117,350,'LEARN   •   PRACTICE   •   BUILD',21,'#a6b8db')
  txt(im,115,425,'บทที่ 1 : ชนิดข้อมูลและตัวแปร' if n==1 else 'ขอบคุณที่เรียนด้วยกัน',30,'#f5f8ff')
  txt(im,115,486,'DATA TYPES & VARIABLES' if n==1 else 'แล้วพบกันใหม่ในบทเรียนหน้า',23,'#a78bfa')
 elif n==2:
  txt(im,75,215,'ตัวแปร = กล่องสำหรับเก็บข้อมูล',30,'#a5edfa')
  box(im,(225,302,650,528),'#142c3c','#34d7ee');txt(im,390,325,'age',32,'#57dff5');txt(im,392,369,'17',75,'#ffffff')
  txt(im,183,570,'ชื่อกล่อง age เก็บข้อมูลอายุ 17',25)
 elif n==3:
  entries=[('int','จำนวนเต็ม','เช่น 10, 25','#ffa6af'),('float','ทศนิยม','เช่น 8.5','#71ddff'),('char','อักขระ 1 ตัว',"เช่น 'A', 'B'",'#ffd56a'),('double','ทศนิยมละเอียดสูง','โดยทั่วไปละเอียดกว่า float','#c4b5fd')]
  for i,(a,b,c,col) in enumerate(entries):
   x=67+(i%2)*380;y=215+(i//2)*210;box(im,(x,y,x+356,y+185));txt(im,x+25,y+9,a,33,col);txt(im,x+25,y+63,b,25);txt(im,x+25,y+115,c,20,'#adbedc')
 elif n==4:
  txt(im,73,220,'ชนิดข้อมูล   ชื่อตัวแปร = ค่า;',27,'#afc5e4');box(im,(76,315,804,430),'#081322','#31526e')
  mono_text(im,110,340,'int age = 17;',48,'#75e5ff');txt(im,78,477,'ประกาศตัวแปร age เก็บจำนวนเต็ม 17',25);txt(im,78,530,'อย่าลืมเครื่องหมาย ; ท้ายคำสั่ง',25,'#ffd56a')
 elif n==5:
  box(im,(62,207,565,643),'#0a1222','#37506e');txt(im,80,215,'main.c',19,'#82e8f5')
  code=['#include <stdio.h>','','int main() {','  int age = 17;','  float score = 85.5;','  char grade = \'A\';','','  printf("Age: %d\\n", age);','  printf("Score: %.1f\\n", score);','  printf("Grade: %c\\n", grade);','','  return 0;','}']
  mono_text(im,80,254,'\n'.join(code),19,'#e1eaff')
  box(im,(583,207,819,420),'#082319','#297454');txt(im,600,220,'OUTPUT',20,'#8ff0b8');mono_text(im,600,270,'Age: 17\nScore: 85.5\nGrade: A',18,'#d0f8df')
  txt(im,592,456,'%d : จำนวนเต็ม',18,'#a7bcdd');txt(im,592,494,'%.1f : ทศนิยม',18,'#a7bcdd');txt(im,592,532,'%c : อักขระ',18,'#a7bcdd')
 elif n==6 or n==7:
  txt(im,75,207,'คะแนน 90.5 ควรใช้ชนิดข้อมูลใด?',27,'#edfaff')
  for i,s in enumerate(['A.  int','B.  float','C.  char']):
   y=280+i*85;correct=n==7 and i==1;box(im,(76,y,700,y+68),'#123e35' if correct else '#1c2b45','#36d3a1' if correct else '#39516e');txt(im,98,y+7,s,27,'#a8f6c9' if correct else '#edf5ff')
  if n==7:txt(im,76,565,'90.5 เป็นทศนิยม จึงใช้ float ได้',24,'#92f4c4')
  elif count:txt(im,730,330,str(count),60,'#ffd56a')
  else:txt(im,76,565,'ลองคิดคำตอบก่อนเฉลย',24,'#a8c0df')
 out=f'{OUT}/scene{n}.png' if count is None else f'{OUT}/count{count}.png'; im.save(out)
for i in range(1,9):make(i)
for i in range(1,6):make(6,i)
print('slides ready')
