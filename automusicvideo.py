
#TODO avoid shell=True

import subprocess
import os
import re
import sys
import mido
import random

from joblib import Memory
memory = Memory(cachedir='temp', verbose=0)
#----------------------------------------------
#                  settings
#----------------------------------------------

inputmidifile = 'input/sufgroove.mid'
trackname = u'VideoTrack'
inputvideofiles = ["input/boop.mp4"]
soundtrack = 'input/sufgroove.wav'

outputfile = 'output/runningman3.mp4'

intermediaryformat=['-an','-c:v','copy']
#intermediaryformat=['-an','-c:v', 'libx264', '-vf','scale=-1:720','-r','25']

#libfaac
outputformat=['-c:a','aac', '-b:a:0', '128k', '-c:v','copy']
#outputformat=['-c:v', 'libx264', '-vf','scale=-1:720', '-c:a','libfaac', '-b:a:0', '128k']


userandomseeks = False


ffmpeg = "ffmpeg\\bin\\ffmpeg.exe"
#ffmpeg ="ffmpeg"
#ffprobe= 'ffprobe'
ffprobe= "ffmpeg\\bin\\ffprobe.exe"
#----------------------------------------------


def getcutsfrommidi(filename,miditrackname):
	mid = mido.MidiFile(filename)
	tempo=500000.0
	for message in mid:
		if isinstance(message, mido.MetaMessage):
			if message.type == 'set_tempo':
				tempo = float(message.tempo)
	time=0.0
	lastcuttime=0.0
	cuts=[ ]
	seconds_per_beat = tempo / 1000000.0
	seconds_per_tick = seconds_per_beat / float(mid.ticks_per_beat)
	#time_in_seconds = time_in_ticks * seconds_per_tick

	for i, track in enumerate(mid.tracks):
		print(repr(track.name))
		if track.name==miditrackname: 
			for message in track:
				if (message.time>0): time=time+float(message.time)*seconds_per_tick
				if not isinstance(message, mido.MetaMessage):
					if (message.type=='note_on')&(time>lastcuttime):
						if (len(cuts)==0)&(time>0):
							seekpercentage=0
							if userandomseeks: seekpercentage =random.random()
							cuts.append({'time': 0, 'video': 0, 'seekpct': seekpercentage}) #first cut has to be at zero
						videoindex = (message.note - 60) % 12 #c is first video file
						seekpercentage = float(message.velocity)/127.0
						if userandomseeks: seekpercentage = random.random() 
						seekpercentage = seekpercentage *.93 +.04
						
						cuts.append({'time': time, 'video': videoindex, 'seekpct': seekpercentage})
						lastcuttime = time
	cuts.append({'time': mid.length, 'video': None, 'seekpct': None})
	return cuts

cuts=getcutsfrommidi(inputmidifile,trackname)

print(cuts)


class VideoFile:
	def __init__(self,filename):
		self.filename = filename
		self._duration = None
		self._iframes = None

	@property
	def duration(self):
		if not (self._duration is None): return self._duration
		cmd = [ffprobe,'-v','error','-select_streams','v:0', \
		       '-show_entries','stream=duration', \
		       '-of','default=noprint_wrappers=1:nokey=1',self.filename]
		#print " ".join(cmd)
		line = subprocess.check_output(cmd)
		self._duration =float(line)
		return self._duration

	#todo: percache?
	@property
	@memory.cache
	def iframes(self):
		if not (self._iframes is None): return self._iframes
		framecachefile =self.filename +'.fcache'	
		cmd = [ffprobe,'-select_streams','v','-show_frames', \
		       '-show_entries','frame=key_frame,pict_type,pkt_pts_time,pkt_duration_time', \
		       '-of','csv',self.filename]
		#print " ".join(cmd)

		with open(os.devnull, 'w') as devnull:
			cmd = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=devnull)
		iframes = []
		lastframepos=0
		for line in cmd.stdout:
			match = re.match(r'^frame,(\d),([\d\.]+),([\d\.]+)',line.decode('utf-8'))
			curframepos=float(match.group(2))
			frametime=curframepos-lastframepos;
			if match.group(1) == '1':
				#use previous frame: http://stackoverflow.com/questions/14005110/how-to-split-a-video-using-ffmpeg-so-that-each-chunk-starts-with-a-key-frame
				iframes.append(lastframepos-frametime*2)
			lastframepos=curframepos
		self._iframes = iframes
		return self._iframes



for idx, item in enumerate(inputvideofiles):
   inputvideofiles[idx] = VideoFile(item)
   print(inputvideofiles[idx].duration)




# start producing files with short clips to be joined.

curpos=0 #this is how many seconds already accounted for. 
clips=[]
for ix in range(0,len(cuts)-1):
	clip = os.path.join('temp','temp_%04i.mp4' % (ix) )
	cut=cuts[ix]
	sourcevideo = inputvideofiles[cut['video'] % len(inputvideofiles)]
	cliplen = cuts[ix+1]['time'] - curpos
	lastfeasibleidx = 0
	for idx,iframe in enumerate(sourcevideo.iframes):
		if (iframe + cliplen < sourcevideo.duration):
			lastfeasibleidx = idx
	print(clip)
	print(repr(cut))
	seektime = sourcevideo.iframes[int(idx*cut['seekpct'])] 
	if seektime>0:
		cmd=[ffmpeg,'-i',sourcevideo.filename,'-ss','%.7f' % (seektime),'-t','%.7f' % (cliplen),'-y']+intermediaryformat
	else:
		cmd=[ffmpeg,'-i',sourcevideo.filename,'-t','%.7f' % (cliplen),'-y']+intermediaryformat		
	cmd.append(clip)
	print(" ".join(cmd))
	with open(os.devnull, 'w') as devnull:
		subprocess.call(cmd,stderr=devnull)
	clipvid=VideoFile(clip)
	clips.append(clip)
	curpos = curpos + clipvid.duration
	print(curpos)


#-----------------JOIN CLIPS------------------

concatfile=os.path.join('temp','concat.txt')
with open(concatfile, "w") as text_file:
	for clip in clips:
		text_file.write("file '%s'\n" % clip.replace('\\', '/')) 


cmd = [ffmpeg,'-f','concat','-i',concatfile, \
       '-i',soundtrack]
cmd += outputformat
cmd.append('-y')
cmd.append(outputfile)

print(" ".join(cmd))
subprocess.call(cmd)


