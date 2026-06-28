from __future__ import annotations
import argparse
import json
import queue
import threading
import time
from pathlib import Path
import voice  # noqa: F401

def _show_notices() -> None:
    p = Path(__file__).resolve().parents[1] / ".claude" / "data" / "voice_notices.jsonl"
    if not p.exists():
        return
    raw = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    entries = [json.loads(l) for l in raw]
    unread = [e for e in entries if not e.get("read")]
    if not unread:
        return
    print(f"\n[{len(unread)} notice(s) while you were away]")
    for n in unread:
        tag = "[!]" if n.get("level") == "URGENT" else "[i]"
        print(f"  {tag} {n['text']}")
    print()
    for e in entries:
        e["read"] = True
    p.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")



def _start_proactive_speaker(
    speak_queue: "queue.Queue[str]",
    stop_event: threading.Event,
) -> threading.Thread:
    """Daemon thread: speaks items heartbeat pushes to speak_queue."""
    def _loop() -> None:
        while not stop_event.is_set():
            try:
                text = speak_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            try:
                from voice import config as cfg
                if cfg.is_quiet_hours():
                    continue
                from voice.tts import speak
                speak(text)
            except Exception as _e:
                print(f"[proactive-tts] error: {_e}", flush=True)

    t = threading.Thread(target=_loop, daemon=True, name="vesper-proactive-speaker")
    t.start()
    return t


def run() -> None:
    parser = argparse.ArgumentParser(description="Vesper voice assistant")
    parser.add_argument("--voice",    action="store_true", help="Push-to-talk voice mode")
    parser.add_argument("--wakeword", action="store_true", help="Always-on wake-word mode (requires openwakeword)")
    args = parser.parse_args()
    # Default to wakeword mode when no flag is given
    if not args.voice and not args.wakeword:
        args.wakeword = True
    if args.wakeword:
        args.voice = True  # wakeword implies voice

    from voice.brain import Brain
    from voice import config as cfg
    conf = cfg.load()
    brain = Brain()

    _show_notices()
    print("Vesper. Ctrl-C to quit.")
    _ww_engine = conf.get("wakeword_engine", "openwakeword")
    if args.wakeword:
        import importlib.util
        if _ww_engine == "vosk":
            if importlib.util.find_spec("vosk") is None:
                print("vosk not installed — using PTT.  (py -m pip install vosk)")
                args.wakeword = False
            else:
                print(f"Listening for wake word: '{conf.get('wakeword_keyword', 'vesper')}' (vosk).")
        else:
            if importlib.util.find_spec("openwakeword") is None:
                print("openwakeword not installed — using PTT.  (pip install openwakeword)")
                args.wakeword = False
            else:
                _ww_model_display = conf.get("wakeword_model", "") or "alexa (fallback)"
                print(f"Listening for wake word (model: {_ww_model_display}).")
    if not args.wakeword and args.voice:
        print(f"Hold [{conf.get('ptt_key', 'space')}] to speak.")
    print()

    # Reflects actual playback state from tts._play — wakeword/clap check this
    from voice.tts import speaking as _tts_active

    # Wake-word thread signals this event; main loop blocks on it instead of PTT
    _wakeword_event: threading.Event | None = None
    _wakeword_stop:  threading.Event | None = None
    if args.wakeword:
        _wakeword_event = threading.Event()
        _wakeword_stop  = threading.Event()
        _wakeword_ready = threading.Event()

        def _on_wake():
            _wakeword_event.set()

        from voice import wakeword as _ww
        if _ww_engine == "vosk":
            _ww_kwargs: dict = {
                "callback":    _on_wake,
                "stop_event":  _wakeword_stop,
                "keyword":     conf.get("wakeword_keyword", "vesper"),
                "model_path":  conf.get("wakeword_model", ""),
                "ready_event": _wakeword_ready,
                "mute_event":  _tts_active,
            }
            _ww_target = _ww.listen_vosk
        else:
            _ww_kwargs = {
                "callback":    _on_wake,
                "stop_event":  _wakeword_stop,
                "model_path":  conf.get("wakeword_model", ""),
                "threshold":   float(conf.get("wakeword_threshold", 0.5)),
                "ready_event": _wakeword_ready,
                "mute_event":  _tts_active,
            }
            _ww_target = _ww.listen
        _ww_thread = threading.Thread(
            target=_ww_target, kwargs=_ww_kwargs,
            daemon=True, name="vesper-wakeword",
        )
        _ww_thread.start()

    # Auto-launch apps on startup
    _startup_shortcuts = conf.get("app_shortcuts", {})
    if _startup_shortcuts:
        from voice.tools.launch_app import launch_app as _launch_app
        for _name in list(_startup_shortcuts.keys()):
            try:
                _launch_app(_name)
                print(f"[startup] opened {_name}", flush=True)
            except Exception as _e:
                print(f"[startup] {_name} failed: {_e}", flush=True)

    # Proactive TTS: heartbeat pushes spoken text here; proactive speaker thread consumes it
    speak_queue: queue.Queue[str] = queue.Queue()
    proactive_tts = bool(conf.get("proactive_tts", True))
    _stop_proactive = threading.Event()

    hb = None
    if conf.get("heartbeat_enabled", True):
        from voice.heartbeat import Heartbeat
        hb = Heartbeat(
            interval_minutes=int(conf.get("heartbeat_interval_minutes", 30)),
            speak_queue=speak_queue,
            proactive_tts=proactive_tts,
        )
        hb.start()

    # Proactive speaker runs only in voice mode; text mode drains via loop
    if args.voice and proactive_tts:
        _start_proactive_speaker(speak_queue, _stop_proactive)

    ui_port = int(conf.get("ui_port", 7070))
    if conf.get("ui_enabled", False):
        from voice import ui_server, tray
        ui_server.start(port=ui_port)
        ui_server.set_brain(brain)
        tray.start(port=ui_port)

    def _emit(event: dict) -> None:
        try:
            from voice import ui_server as _ui
            _ui.post_event(event)
        except Exception:
            pass

    try:
        while True:
            # Text mode: drain and print any proactive messages before prompting
            if not args.voice:
                while True:
                    try:
                        text = speak_queue.get_nowait()
                        print(f"vesper: {text}")
                    except queue.Empty:
                        break

            if args.voice:
                from voice.audio import record_ptt
                from voice.stt import transcribe
                from voice.tts import stop_speaking

                if _wakeword_event is not None:
                    if not _ww_thread.is_alive():
                        print("[wakeword] thread exited — using PTT fallback")
                        _wakeword_event = None
                    else:
                        # Wait for wake word — idle state is managed by on_done / error paths
                        _wakeword_event.wait()
                        _wakeword_event.clear()
                        stop_speaking()
                        print("[wake] triggered — listening …", flush=True)
                        _emit({"type": "state", "value": "listening"})
                        from voice.audio import record_vad
                        audio = record_vad()
                        if audio is None:
                            _wakeword_ready.set()
                            _emit({"type": "state", "value": "idle"})
                            continue
                        try:
                            user_text = transcribe(audio)
                        except Exception as _stt_err:
                            print(f"\n[STT error] {_stt_err}")
                            _wakeword_ready.set()
                            _emit({"type": "state", "value": "idle"})
                            continue
                        if not user_text.strip():
                            print("[STT] (nothing transcribed)")
                            _wakeword_ready.set()
                            _emit({"type": "state", "value": "idle"})
                            continue
                        print(f"[STT] {user_text!r}")
                        # Skip the PTT block below
                        print("vesper: ", end="", flush=True)
                        chunks: list[str] = []
                        for chunk in brain.turn(user_text):
                            print(chunk, end="", flush=True)
                            chunks.append(chunk)
                        print()
                        if chunks and not cfg.is_quiet_hours():
                            from voice.tts import speak
                            _emit({"type": "state", "value": "speaking"})
                            def _after_speak():
                                _wakeword_ready.set()
                                _emit({"type": "state", "value": "idle"})
                            speak("".join(chunks), on_done=_after_speak)
                        else:
                            _wakeword_ready.set()
                            _emit({"type": "state", "value": "idle"})
                        continue

                # PTT path (used when wakeword is off or fell back)
                _emit({"type": "state", "value": "listening"})
                audio = record_ptt(key=conf.get("ptt_key", "space"), on_press=stop_speaking)
                if audio is None:
                    _emit({"type": "state", "value": "idle"})
                    continue
                try:
                    user_text = transcribe(audio)
                except Exception as _stt_err:
                    print(f"\n[STT error] {_stt_err}")
                    _emit({"type": "state", "value": "idle"})
                    continue
                if not user_text.strip():
                    _emit({"type": "state", "value": "idle"})
                    continue
            else:
                try:
                    user_text = input("you: ").strip()
                except EOFError:
                    break
                if not user_text:
                    continue

            print("vesper: ", end="", flush=True)
            chunks: list[str] = []
            for chunk in brain.turn(user_text):
                print(chunk, end="", flush=True)
                chunks.append(chunk)
            print()

            if args.voice and chunks and not cfg.is_quiet_hours():
                from voice.tts import speak
                _emit({"type": "state", "value": "speaking"})
                speak("".join(chunks), on_done=lambda: _emit({"type": "state", "value": "idle"}))
            elif args.voice:
                _emit({"type": "state", "value": "idle"})

    except KeyboardInterrupt:
        _stop_proactive.set()
        if hb:
            hb.stop()
        if _wakeword_stop:
            _wakeword_stop.set()
        print("\nGoodbye.")

if __name__ == "__main__":
    run()
