#!/usr/bin/env python3
"""Convert the VOCAL of one audio clip to Chihaya Anon's voice, then mix the
converted vocal back with the ORIGINAL accompaniment.

Run with the RVC runtime python:
    python cover_one.py --input in.mp3 --output out.wav
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time

ROOT = r"D:\qqaibot\voice\rvc\RVC20260718Nvidia"
INDEX = r"D:\qqaibot\voice\models\anon\anon.index"
UVR_MODEL = "HP5_only_main_vocal.pth"


def log(msg):
    print("[anon] %s" % msg, flush=True)


def separate_vocals(cfg, input_path, workdir):
    """UVR5 分离人声/伴奏，返回 (vocal_wav, inst_wav|None)。"""
    from tools.uvr5.vr import AudioPre

    vocal_dir = os.path.join(workdir, "vocal")
    inst_dir = os.path.join(workdir, "inst")
    model_path = os.path.join(ROOT, "assets", "uvr5_weights", UVR_MODEL)
    t0 = time.time()
    pre = AudioPre(
        agg=10, model_path=model_path,
        device=cfg.device, is_half=cfg.is_half, tta=False,
    )
    pre._path_audio_(input_path, ins_root=inst_dir, vocal_root=vocal_dir, format="wav")
    vocals = sorted(f for f in os.listdir(vocal_dir) if f.startswith("vocal_"))
    insts = sorted(f for f in os.listdir(inst_dir) if f.startswith("instrument_"))
    if not vocals:
        raise RuntimeError("人声分离失败")
    vp = os.path.join(vocal_dir, vocals[0])
    ip = os.path.join(inst_dir, insts[0]) if insts else None
    log("分离完成 %.1fs -> %s" % (time.time() - t0, os.path.basename(vp)))
    return vp, ip


def mix(vocal_path, inst_path, out_path):
    """转换后的人声 + 原伴奏混音（音量补偿 + 限幅）。"""
    ff = os.path.join(ROOT, "ffmpeg.exe")
    chain = ("[0:a]volume=1.0[v];[1:a]volume=0.9[b];"
             "[v][b]amix=inputs=2:duration=longest,volume=1.9,"
             "alimiter=limit=0.95:level=0[o]")
    subprocess.run(
        [ff, "-y", "-i", vocal_path, "-i", inst_path,
         "-filter_complex", chain, "-map", "[o]", "-ar", "44100", out_path],
        check=True, capture_output=True, timeout=180,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--pitch", type=int, default=0)
    p.add_argument("--no-separate", action="store_true")
    p.add_argument("--with-instrumental", action="store_true",
                   help="混回伴奏（默认不混，只输出人声）")
    args = p.parse_args()

    sys.argv = [sys.argv[0]]          # configs.config 会解析 argv，先清空
    os.chdir(ROOT)
    sys.path.insert(0, ROOT)
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("no_proxy", "localhost, 127.0.0.1, ::1")
    os.environ.setdefault("weight_root", "assets/weights")
    os.environ.setdefault("weight_pymss_root", "assets/pymss_weights")
    os.environ.setdefault("index_root", "logs")
    os.environ.setdefault("outside_index_root", "assets/indices")
    os.environ.setdefault("rmvpe_root", "assets/rmvpe")

    import soundfile as sf
    from configs.config import Config
    from infer.vc.modules import VC

    cfg = Config()
    workdir = tempfile.mkdtemp(prefix="anon_vc_")
    t_all = time.time()

    src = os.path.abspath(args.input)
    inst = None
    if not args.no_separate:
        try:
            src, inst = separate_vocals(cfg, src, workdir)
        except Exception as e:
            log("分离失败，改为整段变声: %s" % str(e)[:80])
            inst = None

    vc = VC(cfg)
    vc.get_vc("anon.pth")
    t0 = time.time()
    status, result = vc.vc_single(
        0, src, args.pitch, "rmvpe", INDEX, 0.75, 0, 0.25, 0.33
    )
    if result is None or result[1] is None:
        sys.exit("convert failed")
    sr, audio = result
    log("人声变声完成 %.1fs" % (time.time() - t0))

    out_dir = os.path.dirname(os.path.abspath(args.output))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    raw = os.path.join(workdir, "anon_vocal.wav")
    sf.write(raw, audio, sr)

    if inst and args.with_instrumental:
        mix(raw, inst, args.output)
        log("已与伴奏混音")
    else:
        import shutil
        shutil.copyfile(raw, args.output)
        log("仅输出人声（已去掉伴奏）")

    log("完成 %.1fs -> %s" % (time.time() - t_all, args.output))


if __name__ == "__main__":
    main()
