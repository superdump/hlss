hlss - HTTP Live Streaming Server
=================================


## What is it?

Stream A/V files from any format supported by GStreamer over HLS.

HLSS is a very basic (at the time of writing) on-demand HLS streaming server
that has been thrown together for educational purposes.

## Dependencies

* Python
* gevent
* Flask
* pygi
* GStreamer 1.x and plugins:
    * Various sources, demuxers, parsers and decoders to support your
      input files
    * voaacenc
    * x264enc
    * mpegtsmux
    * multifilesink

## Installation

Nothing to build, just clone it somewhere.

## Usage

```
python /path/to/hlss.py /path/to/media/file
```

Connect to http://localhost:5000/ from a device that can play HLS streams and
knows about the HLS playlist mime type - e.g. an iOS or Android device.

Click the link to open the HLS stream in the media player of your choice.
Alternatively copy the link and paste it into your HLS media player of choice.

## Why did you write it?

I wanted to play around with Python and GStreamer 1.0, and I wanted to see if I
could get HLS working for a use case for which it is not really designed -
on-demand streaming of files.


## How does it work?

HLS streaming requires a few components:

* An HTTP server
* Source media
* Something to transform the source media into HLS
* Pixie dust

The workflow is as follows:
* On the first GET request for the HLS playlist, a GStreamer pipeline is
  created that transcodes (dumbly - no transmuxing) whatever input media file
  you have to a regular HLS stream.

**Note:** HLS client devices require that ~3 segment files are present for
immediate download as soon as the playlist is made available and may barf in
various ways if not. This results in...

* Once the pipeline is started, we wait for 3 segment files to have completed,
  serialize the HLS playlist and finally provide the response to the GET
  request.
* As the pipeline continues processing and completes new segment files, the
  playlist is updated accordingly.
* The HLS client should then start requesting the segment files and then
  repeatedly polls the server for the playlist file so that the client receives
  updates about newly-available segments.

And that's about it.
