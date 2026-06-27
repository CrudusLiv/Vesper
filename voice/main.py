from __future__ import annotations
import argparse
import json
from pathlib import Path
import voice  # noqa: F401

def _show_notices() -> None:
    p = Path(__file__).resolve().parents[1] / "data" / "voice_notices.jsonl"
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

def run() -> None:
    parser = argparse.ArgumentParser(description="Vesper voice assistant")
    parser.add_argument("--voice",    action="store_true", help="Push-to-talk voice mode")
    parser.add_argument("--wakeword", action="store_true", help="Always-on wake-word mode (requires openwakeword)")
    args = parser.parse_args()
    if args.wakeword:
        args.voice = True  # wakeword implies voice

    from voice.brain import Brain
    from voice import config as cfg
    conf = cfg.load()
    brain = Brain()

    _show_notices()
    print("Vesper. Ctrl-C to quit.")
    if args.wakeword:
        import importlib.util
        if importlib.util.find_spec("openwakeword") is None:
            print("openwakeword not installed — using PTT.  (pip install openwakeword to enable wake word)")
            args.wakeword = False
        else:
            _ww_model_display = conf.get("wakeword_model", "") or "alexa (fallback)"
            print(f"Listening for wake word (model: {_ww_model_display}).")
    if not args.wakeword and args.voice:
        print(f"Hold [{conf.get('ptt_key', 'space')}] to speak.")
    print()

    # Wake-word thread signals this event; main loop blocks on it instead of PTT
    _wakeword_event: threading.Event | None = None
    _wakeword_stop:  threading.Event | None = None
    if args.wakeword:
        import threading as _threading
        _wakeword_event = _threading.Event()
        _wakeword_stop  = _threading.Event()
        _wakeword_ready = _threading.Event()

        def _on_wake():
            _wakeword_event.set()

        from voice import wakeword as _ww
        _ww_thread = _threading.Thread(
            target=_ww.listen,
            kwargs={
                "callback":    _on_wake,
                "stop_event":  _wakeword_stop,
                "model_path":  conf.get("wakeword_model", ""),
                "threshold":   float(conf.get("wakeword_threshold", 0.5)),
                "ready_event": _wakeword_ready,
            },
            daemon=True, name="vesper-wakeword",
        )
        _ww_thread.start()

    hb = None
    if conf.get("heartbeat_enabled", True):
        from voice.heartbeat import Heartbeat
        hb = Heartbeat(interval_minutes=int(conf.get("heartbeat_interval_minutes", 30)))
        hb.start()

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
            if args.voice:
                from voice.audio import record_ptt
                from voice.stt import transcribe
                from voice.tts import stop_speaking

                if _wakeword_event is not None:
                    if not _ww_thread.is_alive():
                        print("[wakeword] thread exited — using PTT fallback")
                        _wakeword_event = None
                    else:
                        # Wait for wake word, then record via VAD (no PTT needed)
                        _emit({"type": "state", "value": "idle"})
                        _wakeword_event.wait()
                        _wakeword_event.clear()
                        stop_speaking()
                        _emit({"type": "state", "value": "listening"})
                        from voice.audio import record_vad
                        audio = record_vad()
                        _wakeword_ready.set()  # stream closed — wakeword can reopen
                        if audio is None:
                            _emit({"type": "state", "value": "idle"})
                            continue
                        user_text = transcribe(audio)
                        if not user_text.strip():
                            _emit({"type": "state", "value": "idle"})
                            continue
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
                            speak("".join(chunks))
                        _emit({"type": "state", "value": "idle"})
                        continue

                # PTT path (used when wakeword is off or fell back)
                _emit({"type": "state", "value": "listening"})
                audio = record_ptt(key=conf.get("ptt_key", "space"), on_press=stop_speaking)
                if audio is None:
                    _emit({"type": "state", "value": "idle"})
                    continue
                user_text = transcribe(audio)
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
                speak("".join(chunks))
                _emit({"type": "state", "value": "idle"})
            elif args.voice:
                _emit({"type": "state", "value": "idle"})

    except KeyboardInterrupt:
        if hb:
            hb.stop()
        if _wakeword_stop:
            _wakeword_stop.set()
        print("\nGoodbye.")

if __name__ == "__main__":
    run()
