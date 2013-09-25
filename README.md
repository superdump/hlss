hlss - HTTP Live Streaming Server
=================================


## What is it?

Stream A/V files from any format supported by GStreamer over HLS.

HLSS is a very basic (at the time of writing) on-demand HLS streaming server
that has been thrown together for educational purposes.


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
* Run script providing the path to the media file desired to be served
* Connect to HTTP server (currently http://localhost:5000/ for testing) to get
  the index page with a link to an HLS playlist for the media file
* Click the link to open the HLS stream in the media player of your choice

Here comes the fun part...
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

## Installation

### Dependencies

* Python
* gevent
* Flask
* pygi
* GStreamer and plugins:
    * Various sources, demuxers, parsers and decoders to support your
      input files
    * voaacenc
    * x264enc
    * mpegtsmux
    * multifilesink

TODO

### Deployment

TODO

## Caveats

As this was done for educational purposes, the implementation is lacking:
* awareness of sessions
* error checking
* code-cleanliness
* security
* clean-up of segment files using some kind of stale-ness
* browseable directory structure in HTML instead of a single media 'Click me'
  link
* other bits and pieces to make it generally usable
