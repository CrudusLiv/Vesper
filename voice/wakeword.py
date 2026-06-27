"""Wake-word detection via openwakeword.

Always-on mic stream; calls callback() each time the configured phrase fires.

IMPORTANT: the sounddevice InputStream is *closed* before callback() is
invoked so that record_vad() can open its own stream without conflict.
If a ready_event is passed, the wakeword thread waits for it to be set
before reopening the stream — set it from main.py after VAD finishes.

Install:
    pip install openwakeword sounddevice numpy
    py -c "from openwakeword.utils import download_models; download_models()"

Built-in models (after download): alexa, hey_mycroft, hey_jarvis, hey_rhasspy
Set config.json "wakeword_model" to any of those names or a .onnx path.
"""
from __future__ import annotations

import threading
import time
from typing import Callable

SAMPLE_RATE = 16_000
CHUNK_SIZE = 1280  # ~80 ms at 16 kHz — openwakeword's recommended chunk


def listen(
    callback: Callable[[], None],
    stop_event: threading.Event | None = None,
    model_path: str = "",
    threshold: float = 0.5,
    ready_event: threading.Event | None = None,
) -> None:
    """Block; call callback() each time the wake word fires.

    callback:    Called with the stream CLOSED so record_vad() can open its own.
    stop_event:  Set to exit cleanly.
    model_path:  .onnx path or openwakeword model name; falls back to 'alexa'.
    threshold:   Detection confidence 0–1.
    ready_event: Main thread sets this after VAD recording finishes.
                 Wakeword waits on it before reopening the stream.
    """
    try:
        import numpy as np
        import sounddevice as sd
        from openwakeword.model import Model  # type: ignore
    except ImportError as exc:
        print(f"[wakeword] openwakeword not installed — falling back to PTT  ({exc})")
        if stop_event:
            stop_event.set()
        return

    _name = model_path or "alexa"
    try:
        oww = Model(wakeword_models=[_name], inference_framework="onnx")
    except Exception as _e1:
        if _name != "alexa":
            try:
                oww = Model(wakeword_models=["alexa"], inference_framework="onnx")
            except Exception as _e2:
                print(
                    f"[wakeword] model load failed — run:\n"
                    f'  py -c "from openwakeword.utils import download_models; download_models()"\n'
                    f"  ({_e2})"
                )
                if stop_event:
                    stop_event.set()
                return
        else:
            print(
                f"[wakeword] model load failed — run:\n"
                f'  py -c "from openwakeword.utils import download_models; download_models()"\n'
                f"  ({_e1})"
            )
            if stop_event:
                stop_event.set()
            return

    score_key = list(oww.models.keys())[0]

    while stop_event is None or not stop_event.is_set():
        buf: list[float] = []
        fired = False

        def _cb(indata, frames, time_info, status):  # noqa: ARG001
            buf.extend(indata[:, 0].tolist())

        # Open stream; break inner loop when wake word fires (closes stream).
        with sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32",
            blocksize=CHUNK_SIZE, callback=_cb,
        ):
            while stop_event is None or not stop_event.is_set():
                if len(buf) < CHUNK_SIZE:
                    time.sleep(0.02)
                    continue
                chunk = np.array(buf[:CHUNK_SIZE], dtype=np.float32)
                del buf[:CHUNK_SIZE]  # in-place so _cb closure stays valid
                pcm = (chunk * 32767).astype(np.int16)
                score = oww.predict(pcm).get(score_key, 0.0)
                if score >= threshold:
                    fired = True
                    break  # exits inner loop → with-block closes the stream

        if not fired:
            break  # stop_event was set

        # Stream is now CLOSED. Safe for main thread to call record_vad().
        callback()

        # Wait until main thread signals recording is done, then reopen stream.
        if ready_event:
            ready_event.wait()
            ready_event.clear()
        else:
            time.sleep(3.0)  # fallback debounce when no ready_event provided
