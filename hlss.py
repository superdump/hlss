#! /usr/bin/python

# HLSS - An on-demand HLS streaming server
# Copyright (C) 2013  Robert Swain <robert.swain@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


import sys
from os import path

import urlparse, urllib

import gi
gi.require_version('Gst','1.0')
from gi.repository import GObject, Gst, GstVideo

import gevent
from gevent.wsgi import WSGIServer

from flask import Flask, make_response, render_template, send_file


# this is apparently no longer needed:
# https://bugzilla.gnome.org/show_bug.cgi?id=686914
#GObject.threads_init()
Gst.init(None)

app = Flask(__name__)


class HLSStream:
    def __init__(self, filepath, segment_duration=1):
        self.filepath = filepath

        # make src absolute
        src = path.abspath(path.expanduser(filepath))
        self.src = urlparse.urljoin('file:', urllib.pathname2url(src))

        (path_head, filename) = path.split(src)
        self.filename = filename
        #self.dst = path.join(path_head, "segments")
        self.dst = src
        print "src : " + self.src + "\ndst : " + self.dst + ".%05d.ts"

        self.segment_count = 0
        self.last_stream_time = 0
        self.segment_duration = segment_duration

        self.pipeline = None
        self.playlist = None
        self.eos = False

    def on_eos(self, bus, msg):
        print 'EOS reached'
        self.pipeline.set_state(Gst.State.NULL)
        self.eos = True

    def on_error(self, bus, msg):
        error = msg.parse_error()
        print '*** ERROR *** :', error[1]
        self.pipeline.set_state(Gst.State.NULL)

    def on_element(self, bus, msg):
        structure = msg.get_structure()
        if structure.get_name() != "GstMultiFileSink":
            return

        #filename = structure['filename']
        #duration = msg.structure['stream-time'] - self.last_stream_time
        self.last_stream_time = structure['stream-time']

        self.request_new_segment()

        self.serialize_playlist()

    def create_pipeline(self):
        print "Creating pipeline with:\nsrc: " + self.src + "\ndst: " + self.dst + ".%05d.ts"
        self.pipeline = Gst.parse_launch("uridecodebin uri=" + self.src +
                " name=d ! queue ! x264enc intra-refresh=false aud=1 tune=zerolatency speed-preset=ultrafast key-int-max=90 "
                "! video/x-h264, profile=high ! queue ! mpegtsmux name=m ! " +
                "multifilesink location=" + self.dst + ".%05d.ts sync=true next-file=key-unit-event post-messages=true ")
                #" d. ! queue ! audioconvert ! audio/x-raw, channels=2 ! voaacenc ! queue ! m.")

        self.bus = self.pipeline.get_bus()
        self.bus.set_sync_handler(Gst.Bus.sync_signal_handler, self)
        self.bus.connect('sync-message::eos', self.on_eos)
        self.bus.connect('sync-message::error', self.on_error)
        self.bus.connect('sync-message::element', self.on_element)

        self.pipeline.set_state(Gst.State.PAUSED)

        self.request_new_segment()

        self.pipeline.set_state(Gst.State.PLAYING)

    def request_new_segment(self):
        self.segment_count += 1
        target_time = self.last_stream_time + (self.segment_duration * Gst.SECOND)
        print "Requesting new segment [" + str(self.segment_count) + "] at: " + str(target_time)
        self.pipeline.send_event (GstVideo.video_event_new_upstream_force_key_unit(running_time=target_time, all_headers=True, count=self.segment_count))

    def serialize_playlist(self):
        count = self.segment_count

        if count < 5:
            return

        if count == 5:
            playlist = "#EXTM3U\n#EXT-X-TARGETDURATION:" + \
                    str(self.segment_duration) + "\n#EXT-X-MEDIA-SEQUENCE:0\n"
            for i in range(count):
                playlist += "#EXTINF:" + str(self.segment_duration) + ", no desc\n" \
                        + self.filename + ".{:05d}.ts".format(i) + "\n"
            self.playlist = playlist
        else:
            self.playlist += "#EXTINF:" + str(self.segment_duration) + ", no desc\n" \
                    + self.filename + ".{:05d}.ts".format(count - 1) + "\n"

        if self.eos is True:
            self.playlist += "#EXT-X-ENDLIST\n"


    def get_playlist(self):
        if self.playlist is None:
            if self.pipeline is None:
                print "Creating new pipeline for " + self.filepath
                self.create_pipeline()
            else:
                print "Pipeline but no playlist"

            # not possible to use gevent.Event wait and set here due to the
            # playlist being serialized in a gstreamer thread
            # polling will do for now
            while self.playlist is None:
                gevent.sleep(0.1)
            print "*** Got 3 segments, returning playlist"

        return self.playlist


@app.route('/')
def show_link():
    return render_template('index.html', path=sys.argv[1])

@app.route('/videos/<path:hlspath>')
def render_hls(hlspath):
    resp = None
    hlspath = "/" + hlspath
    print "hit on /videos: " + hlspath

    if hlspath[-5:] == '.m3u8':
        # FIXME - Remove this cheap hack to avoid handling session
        if 'hlspl' not in globals():
            global hlspl
            hlspl = HLSStream(hlspath[0:-5])

        resp = make_response(hlspl.get_playlist())
        resp.mimetype = 'application/x-mpegURL'
    elif hlspath[-3:] == '.ts':
        resp = send_file(hlspath, mimetype='video/MP2T')

    return resp


if __name__ == '__main__':
    if len(sys.argv) == 2:
        app.debug = True
        http_server = WSGIServer(('', 5000), app)
        http_server.serve_forever()
    else:
        print 'Usage: %s /path/to/media/file' % sys.argv[0]
