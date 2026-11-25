from PIL import Image,ImageDraw,ImageOps
from pathlib import Path
import os
R=str(Path(__file__).resolve().parents[2]);O=os.environ.get('RENDER_DIR', '/tmp/kuroya-render');os.makedirs(O, exist_ok=True)
def cut(img):
 img=img.convert('RGB'); temp=img.copy()
 # Flood-fill the light background, preserving light details enclosed by the artwork.
 # The artwork can touch a crop edge and separate the background into
 # several regions, so remove every light region connected to any edge.
 for x in range(0,img.width,3):
  for y in (0,img.height-1):
   pixel=temp.getpixel((x,y))
   if min(pixel)>220: ImageDraw.floodfill(temp,(x,y),(0,255,0),thresh=75)
 for y in range(0,img.height,3):
  for x in (0,img.width-1):
   pixel=temp.getpixel((x,y))
   if min(pixel)>220: ImageDraw.floodfill(temp,(x,y),(0,255,0),thresh=75)
 out=img.convert('RGBA'); alpha=Image.new('L',img.size,255)
 ap=alpha.load();tp=temp.load(); op=img.load()
 for y in range(img.height):
  for x in range(img.width):
   if tp[x,y]==(0,255,0): ap[x,y]=0
 out.putalpha(alpha)
 bbox=alpha.getbbox()
 if bbox:out=out.crop(bbox)
 return out

def canvas(img,filename,maxsize):
 img.thumbnail(maxsize,Image.Resampling.LANCZOS)
 out=Image.new('RGBA',(348,450));out.alpha_composite(img,((348-img.width)//2, (450-img.height)//2))
 out.save(f'{O}/{filename}.png')
main=Image.open(R+'/assets/img/oc-1.jpg').crop((0,0,315,1024));canvas(cut(main),'main',(340,440))
chibi=Image.open(R+'/assets/img/oc-2.jpg')
for n in [0,2,3,5,8,9,13,15]:
 x=n%4*384;y=n//4*256
 img=chibi.crop((x+2,y+2,x+382,y+254));canvas(cut(img),f'chibi{n}',(330,380))
