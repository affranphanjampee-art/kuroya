"""Render the lesson from the checked-in slides, OC references and narrations.
Run: pip install pillow freetype-py uharfbuzz imageio-ffmpeg
     python lesson/tools/render_video.py
"""
import os, re, subprocess, tempfile, sys
from pathlib import Path
import imageio_ffmpeg
root=Path(__file__).resolve().parents[2]
ff=imageio_ffmpeg.get_ffmpeg_exe()
with tempfile.TemporaryDirectory(prefix='codecraft-render-') as tmp:
 env={**os.environ,'RENDER_DIR':tmp}
 for script in ('render_slides.py','render_sprites.py'):
  subprocess.run([sys.executable,str(root/'lesson/tools'/script)],env=env,check=True)
 durations=[]
 for i in range(1,9):
  p=subprocess.run([ff,'-i',str(root/f'assets/audio/scene{i}.mp3')],capture_output=True,text=True)
  h,m,s=map(float,re.search(r'Duration: (\d+):(\d+):([\d.]+)',p.stderr).groups())
  durations.append(h*3600+m*60+s)
 slide_lines=['ffconcat version 1.0']; sprite_lines=['ffconcat version 1.0']
 def entry(lines, filename, duration):
  lines.extend([f"file '{tmp}/{filename}.png'",f'duration {duration:.2f}'])
 pairs=[('main','main'),('chibi0','chibi9'),('chibi0','chibi13'),('chibi9','chibi0'),('chibi0','chibi9'),('chibi3','chibi9'),('chibi13','chibi2'),('main','main')]
 for i,t in enumerate(durations,1):
  entry(slide_lines,f'scene{i}',t)
  if i==6:
   for j in range(5,0,-1):entry(slide_lines,f'count{j}',1)
  total=t+(5 if i==6 else 0)
  elapsed=0; k=0
  while elapsed < total-0.001:
   duration=min(4.0,total-elapsed)
   # The silent countdown uses a thinking expression.
   if i==6 and elapsed>=t: sprite='chibi3'
   else: sprite=pairs[i-1][k%2]
   entry(sprite_lines,sprite,duration)
   elapsed+=duration;k+=1
 slide_lines.append(f"file '{tmp}/scene8.png'")
 sprite_lines.append(f"file '{tmp}/main.png'")
 for name,lines in [('slides',slide_lines),('sprites',sprite_lines)]:
  Path(tmp,f'{name}.ffconcat').write_text('\n'.join(lines)+'\n')
 cmd=[ff,'-hide_banner','-y','-f','concat','-safe','0','-i',f'{tmp}/slides.ffconcat','-f','concat','-safe','0','-i',f'{tmp}/sprites.ffconcat']
 for i in range(1,9):cmd.extend(['-i',str(root/f'assets/audio/scene{i}.mp3')])
 cmd+=['-f','lavfi','-t','5','-i','anullsrc=r=44100:cl=stereo']
 filters=[]
 for i,t in enumerate(durations,1):
  filters.append(f'[{i+1}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={t:.2f},asetpts=PTS-STARTPTS[a{i}]')
 filters.append('[10:a]asetpts=PTS-STARTPTS[quiet]')
 filters.append(''.join(f'[a{i}]' for i in range(1,7))+'[quiet][a7][a8]concat=n=9:v=0:a=1[a]')
 filters.extend([
  '[0:v]fps=25,tpad=stop_mode=clone:stop_duration=18[slides]',
  '[1:v]fps=25,tpad=stop_mode=clone:stop_duration=18,format=rgba[sprites]',
  "[slides][sprites]overlay=x='883+5*sin(t*1.3)':y='201+8*sin(t*2.1)':eval=frame:shortest=1,format=yuv420p[v]"
 ])
 total=sum(durations)+5
 cmd+=['-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-r','25','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-t',str(total),'-movflags','+faststart',str(root/'lesson/CODECRAFT-lesson1-animated.mp4')]
 print(f'Rendering {total:.2f} seconds',flush=True)
 subprocess.run(cmd,check=True)
