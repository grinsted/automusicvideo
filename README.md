# automusicvideo

A messy python script that automatically generates a music video. 

It cuts an input video at I-frames (to minimize re-encoding, and because it is a good indicator of places to cut)

Inputs
* a midi file
  - A note triggers a cut
  - Velocity is used as a time index (unless UseRandomSeeks is True)
  - Note value is used to select a video index
* An audio track
* Some source video material.

Outputs: A music video


Example video: https://youtu.be/zgvcMGsBP4s
