"""Bounded AVC/legacy HEVC + AAC FLV remuxing, without a local decoder."""
import heapq
import os
import time

MAX_TAG = 8 * 1024 * 1024
MAX_SEGMENT = 64 * 1024 * 1024
MAX_WAIT_MS = 15000
REORDER_MS = 250


class Unsupported(ValueError):
    """A fixed parser reason, optionally with the two timestamps that triggered it."""
    def __init__(self, reason, *, previous_ms=None, packet_ms=None):
        super().__init__(reason)
        self.previous_ms = previous_ms
        self.packet_ms = packet_ms


def tag(kind, stamp, payload):
    return (bytes([kind]) + len(payload).to_bytes(3, 'big') +
            (stamp & 0xffffff).to_bytes(3, 'big') + bytes([stamp >> 24]) + b'\0\0\0' +
            payload + (11 + len(payload)).to_bytes(4, 'big'))


class Slicer:
    def __init__(self, root, index, base_ms, seconds, publish):
        self.root, self.index, self.base = root, index, base_ms
        self.target = seconds * 1000
        self.publish = publish
        self.buffer = bytearray()
        self.header = None
        self.config = {}
        self.start = self.origin = self.last = None
        self.output = None
        self.size = 0
        self.audio = False
        self.video = False
        self.pending = []
        self.pending_bytes = self.sequence = 0
        self.latest = None
        self.started_at = time.monotonic()

    def feed(self, data):
        self.buffer.extend(data)
        if self.header is None:
            if len(self.buffer) < 13:return
            if self.buffer[:4] != b'FLV\x01' or self.buffer[4] not in (1, 4, 5):
                raise Unsupported('flv_header')
            if int.from_bytes(self.buffer[5:9], 'big') != 9 or self.buffer[9:13] != b'\0'*4:
                raise Unsupported('flv_header')
            self.header = bytes(self.buffer[:13]); del self.buffer[:13]
            self.video = bool(self.header[4] & 1)
        while len(self.buffer) >= 11:
            kind = self.buffer[0]
            size = int.from_bytes(self.buffer[1:4], 'big')
            if size > MAX_TAG:raise Unsupported('tag_limit')
            if kind not in (8, 9, 18) or self.buffer[8:11] != b'\0'*3:
                raise Unsupported('tag_header')
            if len(self.buffer) < 15 + size:return
            if int.from_bytes(self.buffer[11+size:15+size], 'big') != 11+size:
                raise Unsupported('tag_size')
            stamp = int.from_bytes(self.buffer[4:7], 'big') | self.buffer[7] << 24
            payload = bytes(self.buffer[11:11+size]); del self.buffer[:15+size]
            self.accept(kind, stamp, payload)

    def accept(self, kind, stamp, payload):
        # Discard script metadata (duration/seek indexes describe the original stream).
        # Decoder metadata is supplied by the codec sequence headers below.
        if kind == 18:return
        if len(payload) < (5 if kind == 9 else 2):raise Unsupported('codec_header')
        # Legacy HEVC (CodecID 12) shares AVC's packet type and signed CTS layout.
        # Enhanced FLV uses a different header and still takes the fallback route.
        if kind == 9 and (payload[0] & 0x80 or payload[0] & 15 not in (7, 12)):
            raise Unsupported('video_codec')
        if kind == 8 and payload[0] >> 4 != 10:raise Unsupported('audio_codec')
        if kind == 9 and kind in self.config and payload[0] & 15 != self.config[kind][0] & 15:
            self.close()
            raise Unsupported('codec_changed')
        if payload[1] == 0:
            if self.config.get(kind) == payload:return
            self.drain()
            if kind in self.config and self.config[kind] != payload:
                self.close()
                raise Unsupported('codec_changed')
            if self.output is not None and kind not in self.config:
                chunk=tag(kind,max(0,stamp-self.start),payload)
                self.output.write(chunk);self.size+=len(chunk)
            self.config[kind] = payload
            return
        if payload[1] != 1:
            if kind == 9 and payload[1] == 2:return
            raise Unsupported('packet_type')
        if kind not in self.config:raise Unsupported('sequence_missing')
        if self.latest is not None and (stamp < self.latest - REORDER_MS or stamp-self.latest > MAX_WAIT_MS):
            self.close()
            raise Unsupported('timestamp_discontinuity', previous_ms=self.latest, packet_ms=stamp)
        self.latest = max(stamp, self.latest if self.latest is not None else stamp)
        self.drain(self.latest - REORDER_MS)
        if self.pending_bytes + len(payload) + 15 > MAX_SEGMENT:
            raise Unsupported('segment_limit')
        # Delay publication until interleaved packets can be assigned by DTS.
        # At equal DTS the video keyframe must precede the new interval's audio.
        heapq.heappush(self.pending,(stamp,0 if kind==9 else 1,self.sequence,kind,payload))
        self.sequence += 1
        self.pending_bytes += len(payload) + 15

    def drain(self, before=None):
        while self.pending and (before is None or self.pending[0][0] < before):
            stamp,_,_,kind,payload=heapq.heappop(self.pending)
            self.pending_bytes -= len(payload) + 15
            try:self.write_packet(kind,stamp,payload)
            except Unsupported:
                # Keep the written prefix closable when buffered input exceeds a limit.
                self.pending.clear(); self.pending_bytes = 0
                raise

    def write_packet(self, kind, stamp, payload):
        if self.origin is None:self.origin = stamp
        key = kind == 9 and payload[0] >> 4 == 1
        boundary = key if self.video else kind == 8
        if self.start is not None and stamp-self.start >= self.target and boundary:
            self.close_file(stamp)
        if self.start is None:
            if not boundary:
                if stamp-self.origin > MAX_WAIT_MS:raise Unsupported('keyframe_timeout')
                return
            self.start = stamp
            self.output = (self.root / f'segment-{self.index:06d}.flv.part').open('xb')
            os.chmod(self.output.name, 0o600)
            self.output.write(self.header)
            self.size = len(self.header)
            for codec, config in sorted(self.config.items()):
                chunk = tag(codec, 0, config); self.output.write(chunk); self.size += len(chunk)
        if stamp < self.start:return  # Leading interleaved packet belongs to prior interval.
        if stamp-self.start > self.target + MAX_WAIT_MS:raise Unsupported('keyframe_timeout')
        chunk = tag(kind, stamp-self.start, payload)
        if self.size + len(chunk) > MAX_SEGMENT:raise Unsupported('segment_limit')
        self.output.write(chunk); self.size += len(chunk)
        self.last = max(stamp, self.last or stamp)
        self.audio |= kind == 8

    def close(self, end=None):
        self.drain()
        self.close_file(end)

    def close_file(self, end=None):
        if self.output is None:return
        end = self.last if end is None else end
        handle, self.output = self.output, None
        try:
            handle.flush(); os.fsync(handle.fileno())
        finally:handle.close()
        path = self.root / f'segment-{self.index:06d}.flv'
        if end is not None and end > self.start:
            os.replace(handle.name, path)
            self.publish(self.index, self.base+self.start-self.origin,
                         self.base+end-self.origin, path, self.audio, self.size)
            self.index += 1
        else:os.unlink(handle.name)
        self.start = None; self.audio = False

    def abort(self):
        self.pending.clear()
        self.pending_bytes = 0
        if self.output is not None:
            name = self.output.name
            self.output.close(); self.output = None
            os.unlink(name)
