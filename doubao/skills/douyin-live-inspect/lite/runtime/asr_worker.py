"""Persistent CPU model process. JSON control only; audio never crosses stdout."""
import json
from pathlib import Path
import struct
import sys
import time

# Also works when invoked directly from an unpacked Skill, with no PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.asr_model import MODEL, VERSION, ModelError, checked_model


def dependencies():
    try:
        import numpy as np
        import sherpa_onnx as sherpa
    except (ImportError, OSError):
        raise ModelError('ASR_DEPENDENCY_UNAVAILABLE') from None
    if sherpa.__version__ != VERSION: raise ModelError('ASR_DEPENDENCY_INCOMPATIBLE')
    return np, sherpa


def wav_pcm(data):
    """Strict RIFF/S16LE validator including duplicate/truncated chunks."""
    def invalid(): raise ModelError('ASR_INVALID_PCM')
    if len(data) < 44 or len(data) > 6_000_000 or data[:4] != b'RIFF' or data[8:12] != b'WAVE': invalid()
    if struct.unpack_from('<I', data, 4)[0] + 8 != len(data): invalid()
    offset, pcm, fmt = 12, None, False
    while offset + 8 <= len(data):
        name, size = struct.unpack_from('<4sI', data, offset)
        offset += 8
        if offset + size > len(data): invalid()
        if name == b'fmt ':
            if fmt or size < 16: invalid()
            tag, channels, rate, byte_rate, align, bits = struct.unpack_from('<HHIIHH', data, offset)
            if (tag, channels, rate, byte_rate, align, bits) != (1, 1, 16000, 32000, 2, 16): invalid()
            fmt = True
        elif name == b'data':
            if pcm is not None: invalid()
            pcm = data[offset:offset+size]
        offset += size + size % 2
    if offset != len(data) or not fmt or not pcm or len(pcm) % 2: invalid()
    return pcm


def subtitle(text, begin, end):
    if not isinstance(text, str) or not text.strip(): raise ModelError('ASR_EMPTY_SPEECH')
    result = dict(text=text.replace('<unk>', '〔未识别〕').strip(), start_ms=round(begin/16), end_ms=round(end/16))
    if '<unk>' in text:
        result['asr_quality'] = dict(raw_text=text, unresolved_unknowns=text.count('<unk>'))
    return result


class StreamingRecognizer:
    """One resident model, incremental decoding; only final utterances are evidence."""
    def __init__(self, recognizer, offset_ms=0):
        self.owner=recognizer
        self.rec=recognizer.recognizer
        self.vad=recognizer.vad
        if hasattr(recognizer,'vad_config'):
            config=recognizer.vad_config
            config.silero_vad.max_speech_duration=100
            self.vad=recognizer.sherpa.VoiceActivityDetector(config,buffer_size_in_seconds=200)
            config.silero_vad.max_speech_duration=20
        self.offset_ms=offset_ms
        self.total=self.begin=0
        self.prefix=""
        self.tail=self.owner.np.zeros(0,dtype=self.owner.np.float32)
        self.reset()

    def reset(self,context=None):
        self.stream=self.rec.create_stream()
        self.vad.reset()
        self.vad_origin=self.total
        self.speech=False
        self.prefix=""
        if context is not None and len(context):
            # A silence-only visual boundary may precede the VAD trigger by a
            # few samples. Preserve 200 ms of real audio without adding time.
            self.vad_origin-=len(context)
            self.vad.accept_waveform(context)
            self.stream.accept_waveform(16000,context)
            while self.rec.is_ready(self.stream):self.rec.decode_stream(self.stream)

    def finish_unit(self, continuation=False):
        if self.total==self.begin:return None
        if not continuation:
            self.stream.accept_waveform(16000,self.owner.np.zeros(4800,dtype=self.owner.np.float32))
            self.stream.input_finished()
        while self.rec.is_ready(self.stream):self.rec.decode_stream(self.stream)
        full_text=self.rec.get_result(self.stream)
        # Keep the decoder/acoustic context across the 20-second boundary.
        # Previously finalized text is context only, never emitted twice.
        shared=0
        for a,b in zip(self.prefix,full_text):
            if a!=b:break
            shared+=1
        text=full_text[shared:]
        a=self.offset_ms+round(self.begin/16)
        b=self.offset_ms+round(self.total/16)
        value={'start_ms':a,'end_ms':b,'text':text.replace('<unk>','〔未识别〕').strip(),
               'speech_detected':self.speech,'continuation':continuation,
               'error':'ASR_EMPTY_SPEECH' if self.speech and not text.strip() else None}
        self.begin=self.total
        if continuation:
            self.prefix=full_text
            self.speech=False
        else:self.reset(self.tail if not self.speech and not text.strip() else None)
        return value

    def feed(self,pcm):
        samples=self.owner.np.frombuffer(pcm,dtype='<i2').astype(self.owner.np.float32)/32768.0
        finals=[]
        for pos in range(0,len(samples),1600):
            block=samples[pos:pos+1600]
            self.total+=len(block)
            self.tail=self.owner.np.concatenate((self.tail,block))[-3200:]
            self.vad.accept_waveform(block)
            self.speech=self.speech or self.vad.is_speech_detected() or not self.vad.empty()
            self.stream.accept_waveform(16000,block)
            while self.rec.is_ready(self.stream):self.rec.decode_stream(self.stream)
            duration=self.total-self.begin
            if not self.vad.empty() or duration>=320000 or (not self.speech and duration>=160000):
                if not self.vad.empty() and hasattr(self.vad,'front'):
                    voice=self.vad.front
                    # A VAD endpoint after a continuation may contain only the
                    # previous unit's speech plus this unit's trailing silence.
                    self.speech=self.vad_origin+voice.start+len(voice.samples)>self.begin
                finals.append(self.finish_unit(continuation=duration>=320000))
        return {'finals':finals,'partial':self.rec.get_result(self.stream),
                'start_ms':self.offset_ms+round(self.begin/16),'end_ms':self.offset_ms+round(self.total/16)}

    def finish(self):
        value=self.finish_unit()
        return {'finals':[value] if value else [],'partial':''}


class Recognizer:
    def __init__(self, root):
        self.np, sherpa = dependencies()
        model = root / 'model' / MODEL
        self.recognizer = sherpa.OnlineRecognizer.from_transducer(
            tokens=str(model/'tokens.txt'), encoder=str(model/'encoder.int8.onnx'),
            decoder=str(model/'decoder.onnx'), joiner=str(model/'joiner.int8.onnx'),
            num_threads=2, sample_rate=16000, feature_dim=80, decoding_method='greedy_search',
            enable_endpoint_detection=False, provider='cpu')
        config = sherpa.VadModelConfig()
        config.sample_rate, config.num_threads, config.provider = 16000, 1, 'cpu'
        config.silero_vad.model = str(root/'vad/silero_vad.onnx')
        config.silero_vad.threshold = .5
        config.silero_vad.min_silence_duration = .5
        config.silero_vad.min_speech_duration = .1
        config.silero_vad.max_speech_duration = 20
        config.silero_vad.window_size = 512
        self.vad_config,self.sherpa=config,sherpa
        self.vad = sherpa.VoiceActivityDetector(config, buffer_size_in_seconds=200)

    def transcribe(self, pcm):
        np, vad, rec = self.np, self.vad, self.recognizer
        started = time.monotonic()
        samples = np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768.0
        vad.reset()
        for pos in range(0, len(samples), 512):
            window = samples[pos:pos+512]
            if len(window) < 512: window = np.pad(window, (0, 512-len(window)))
            vad.accept_waveform(window)
        vad.flush()
        ranges = []
        while not vad.empty():
            segment = vad.front
            begin = max(0, segment.start - 2400, ranges[-1][1] if ranges else 0)
            end = min(len(samples), segment.start + len(segment.samples) + 2400)
            if end > begin: ranges.append((begin, end))
            vad.pop()
        output, calls, gaps = [], 0, []
        for low, high in ranges:
            for begin in range(low, high, 320000):
                end = min(begin+320000, high)
                if not np.any(samples[begin:end]): continue
                stream = rec.create_stream()
                for pos in range(begin, end, 5120):
                    stream.accept_waveform(16000, samples[pos:min(pos+5120, end)])
                    while rec.is_ready(stream): rec.decode_stream(stream)
                # Synthetic right context must not extend evidence timestamps.
                stream.accept_waveform(16000, np.zeros(4800, dtype=np.float32))
                stream.input_finished()
                while rec.is_ready(stream): rec.decode_stream(stream)
                try:output.append(subtitle(rec.get_result(stream), begin, end))
                except ModelError as error:
                    if error.code!='ASR_EMPTY_SPEECH':raise
                    gaps.append({'start_ms':round(begin/16),'end_ms':round(end/16),'code':error.code})
                calls += 1
        return dict(subtitles=output, speech_gaps=gaps, duration_ms=len(pcm)/32, processing_ms=round((time.monotonic()-started)*1000),
                    dropped_audio_ms=0, asr_mode='single_pass', asr_calls=calls)


def run():
    recognizer, task_root, streaming, raw_path, raw_offset = None, None, None, None, 0
    # Binary streams avoid Windows newline and locale transformations.
    while True:
        line = sys.stdin.buffer.readline(65537)
        if not line or len(line) > 65536: break
        rid = None
        try:
            request = json.loads(line)
            rid = request['id']
            if not isinstance(rid, str) or len(rid) > 128: raise ModelError('ASR_PROTOCOL_ERROR')
            command = request['command']
            if command in ('check', 'initialize') and recognizer is None:
                dependencies()
                root, value = checked_model(request['runtime_root'])
                if command == 'initialize':
                    task_root = Path(request['task_root']).resolve(strict=True)
                    recognizer = Recognizer(root)
            elif command == 'transcribe' and recognizer:
                path = Path(request['audio_path']).resolve(strict=True)
                if not path.is_relative_to(task_root) or not path.is_file(): raise ModelError('ASR_INVALID_PCM')
                with path.open('rb') as audio: pcm = wav_pcm(audio.read(6_000_001))
                value = recognizer.transcribe(pcm)
            elif command == 'stream-start' and recognizer:
                path=Path(request['audio_path']).resolve(strict=True)
                if not path.is_relative_to(task_root) or not path.is_file():raise ModelError('ASR_INVALID_PCM')
                offset=request.get('byte_offset',0)
                if type(offset) is not int or offset<0 or offset%2 or offset>path.stat().st_size:raise ModelError('ASR_INVALID_PCM')
                timestamp=request.get('offset_ms',0)
                if type(timestamp) is not int or timestamp<0:raise ModelError('ASR_INVALID_PCM')
                raw_path,raw_offset=path,offset
                streaming=StreamingRecognizer(recognizer,request.get('offset_ms',0))
                value={'started':True}
            elif command == 'stream-read' and streaming:
                count=request.get('bytes',3200)
                if type(count) is not int or not 0<count<=32000 or count%2:raise ModelError('ASR_INVALID_PCM')
                with raw_path.open('rb') as audio:
                    audio.seek(raw_offset);pcm=audio.read(count)
                pcm=pcm[:len(pcm)//2*2]
                raw_offset+=len(pcm)
                value={**streaming.feed(pcm),'bytes_read':len(pcm)}
            elif command == 'stream-finish' and streaming:
                value=streaming.finish();streaming=None
            else: raise ModelError('ASR_PROTOCOL_ERROR')
            response = dict(id=rid, ok=True, value=value)
        except Exception as error:
            code = error.code if isinstance(error, ModelError) else 'ASR_PROTOCOL_ERROR'
            response = dict(id=rid, ok=False, error=dict(code=code))
        sys.stdout.buffer.write((json.dumps(response, ensure_ascii=True, allow_nan=False)+'\n').encode('ascii'))
        sys.stdout.buffer.flush()


if __name__ == '__main__': run()
