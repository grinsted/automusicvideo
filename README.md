# automusicvideo

A messy python script that automatically generates a music video. 

It cuts an input video at I-frames, and 

Inputs
* a midi file
  - A note triggers a cut
  - Velocity is used as a time index (unless UseRandomSeeks is True)
  - Note value is used to select a video index
* An audio track
* Some source video material.

Outputs: A music video
