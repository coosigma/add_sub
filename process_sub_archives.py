#!/usr/bin/env python3
"""Extract archives in `sub/`, convert all .srt to .ass with bottom alignment,
and collect resulting .ass files into `output/<archive_name>/`.

Supported archive types: .zip, .tar, .tgz, .tar.gz, .tar.bz2, .tar.xz

Also handles plain .srt/.ass files placed directly in `sub/`.
"""
from __future__ import annotations
import argparse
import subprocess
import shutil
import sys
import tarfile
import zipfile
import tempfile
import re
from pathlib import Path

from srt_to_ass import convert, adjust_ass_styles


def is_supported_archive(p: Path) -> bool:
    return p.suffix.lower() in {".zip", ".tar", ".tgz", ".gz", ".bz2", ".xz"} or p.name.lower().endswith(
        ".tar.gz")


def extract_archive(archive: Path, dest: Path) -> None:
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive, "r") as z:
            z.extractall(dest)
        return
    # try tar
    try:
        with tarfile.open(archive) as t:
            t.extractall(dest)
        return
    except (tarfile.ReadError, Exception):
        pass
    raise RuntimeError(f"Unsupported archive format: {archive}")


def find_sxxexx(s: str) -> str | None:
    m = re.search(r"s(\d{1,2})[\. _-]*e(\d{1,2})", s, re.IGNORECASE)
    if m:
        return f"s{int(m.group(1)):02d}e{int(m.group(2)):02d}"
    return None


def find_best_video_for_ass(ass_path: Path, mp4_list: list[Path]) -> Path | None:
    if not mp4_list:
        return None
    ass_name = ass_path.name.lower()
    ass_parent = ass_path.parent.name.lower()
    sxx = find_sxxexx(ass_name) or find_sxxexx(ass_parent)
    # 1) match by SxxExx
    if sxx:
        for m in mp4_list:
            if sxx in m.name.lower():
                return m
    # 2) exact or partial stem match
    for m in mp4_list:
        if m.stem.lower() in ass_name or ass_path.stem.lower() in m.name.lower():
            return m
    # 3) match by episode number E##
    m_e = re.search(r"e(\d{1,2})", ass_name, re.IGNORECASE)
    if m_e:
        ep = int(m_e.group(1))
        for m in mp4_list:
            me = re.search(r"e(\d{1,2})", m.name, re.IGNORECASE)
            if me and int(me.group(1)) == ep:
                return m
    # 4) attempt to match Chinese naming like '第二季01' or '第2季01'
    def chinese_num_to_int(s: str) -> int | None:
        mapping = {'零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
        # simple conversion for up to 2-digit numbers like '二' or '十' or '十一'
        try:
            # digits
            return int(s)
        except Exception:
            n = 0
            for ch in s:
                if ch in mapping:
                    n = n*10 + mapping[ch]
                else:
                    return None
            return n if n != 0 else None

    # extract sxx numeric from ass if present
    s_se = None
    if sxx:
        m_s = re.match(r"s(\d{2})e(\d{2})", sxx)
        if m_s:
            s_se = (int(m_s.group(1)), int(m_s.group(2)))

    for m in mp4_list:
        name = m.name
        # patterns: 第X季YY or 第X季 YY or X季YY
        m_ch = re.search(r"第([0-9零一二三四五六七八九十]+)季\s*0*([0-9]{1,2})", name)
        if m_ch:
            season_raw = m_ch.group(1)
            ep_raw = m_ch.group(2)
            season = chinese_num_to_int(season_raw)
            ep = int(ep_raw)
            if s_se and season == s_se[0] and ep == s_se[1]:
                return m
            # also if ass doesn't have sxx, match by episode
            if not s_se and ep == (int(m_e.group(1)) if m_e else None):
                return m
    return None


def integrate_ass_into_video(ass_path: Path, video_path: Path) -> Path | None:
    """Try to mux the ASS into a new MKV next to the video using ffmpeg. Return path if created."""
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found; skipping mux for", video_path)
        return None
    out_mkv = video_path.with_suffix("")
    # ensure .mkv suffix
    out_mkv = Path(str(out_mkv) + ".mkv")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(ass_path),
        # map only video and audio from input (exclude data/timed-metadata streams that Matroska rejects)
        "-map",
        "0:v?",
        "-map",
        "0:a?",
        "-map",
        "1",
        "-c",
        "copy",
        "-c:s",
        "copy",
        "-disposition:s:0",
        "default",
        str(out_mkv),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Created muxed file: {out_mkv}")
        return out_mkv
    except subprocess.CalledProcessError:
        print(f"ffmpeg mux failed for {video_path} + {ass_path}")
        return None


def integrate_ass_and_video_to_outdir(ass_path: Path, video_path: Path, outdir: Path) -> Path | None:
    """Create an MKV in outdir by muxing video_path + ass_path. Return created path or None."""
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found; skipping mux for", video_path)
        return None
    outdir.mkdir(parents=True, exist_ok=True)
    base = video_path.stem
    out_mkv = outdir / (base + ".mkv")
    # ensure unique
    i = 1
    while out_mkv.exists():
        out_mkv = outdir / f"{base}_{i}.mkv"
        i += 1
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(ass_path),
        # map only video and audio from input (exclude data/timed-metadata streams that Matroska rejects)
        "-map",
        "0:v?",
        "-map",
        "0:a?",
        "-map",
        "1",
        "-c",
        "copy",
        "-c:s",
        "copy",
        "-disposition:s:0",
        "default",
        str(out_mkv),
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"Created muxed file in output: {out_mkv}")
        return out_mkv
    except subprocess.CalledProcessError:
        print(f"ffmpeg mux failed for {video_path} + {ass_path}")
        return None


def process_subdir(subdir: Path, outdir: Path, temp_root: Path, force_align: str = "bottom-center", mp4_list: list[Path] | None = None, mux: bool = False, margin_v: int | None = None, h_margin: int | None = None, h_margin_pct: int | None = None, play_res_x: int | None = None, play_res_y: int | None = None, outline: float | None = None, shadow: float | None = None) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    temp_root.mkdir(parents=True, exist_ok=True)

    def make_unique(base_name: str) -> Path:
        target = temp_root / base_name
        if not target.exists():
            return target
        stem = Path(base_name).stem
        suf = Path(base_name).suffix
        i = 1
        while True:
            candidate = temp_root / f"{stem}_{i}{suf}"
            if not candidate.exists():
                return candidate
            i += 1

    for item in sorted(subdir.iterdir()):
        if item.is_dir():
            # scan directory content and flatten outputs into outdir
            for f in item.rglob("*"):
                if f.is_file() and f.suffix.lower() == ".srt":
                    name = f.relative_to(item).with_suffix(".ass").name
                    outf = make_unique(name)
                    convert(str(f), str(outf), force_align=force_align)
                    # ensure styles/alignments updated
                    adjust_ass_styles(str(outf), fontname="Arial", fontsize=18, force_align=force_align, margin_v=margin_v, raise_for_24=30, h_margin=h_margin, h_margin_pct=h_margin_pct, play_res_x=play_res_x, play_res_y=play_res_y, outline=outline, shadow=shadow)
                    if mp4_list:
                        mv = find_best_video_for_ass(outf, mp4_list)
                        if mv and mux:
                            created = integrate_ass_and_video_to_outdir(outf, mv, outdir)
                            if created:
                                print(f"Muxed -> {created}")
                elif f.is_file() and f.suffix.lower() == ".ass":
                    name = f.relative_to(item).name
                    dest_f = make_unique(name)
                    shutil.copy2(f, dest_f)
                    # adjust styles in-place
                    adjust_ass_styles(str(dest_f), fontname="Arial", fontsize=18, force_align=force_align, margin_v=margin_v, raise_for_24=30, h_margin=h_margin, h_margin_pct=h_margin_pct, play_res_x=play_res_x, play_res_y=play_res_y, outline=outline, shadow=shadow)
                    if mp4_list and mux:
                        mv = find_best_video_for_ass(dest_f, mp4_list)
                        if mv:
                            created = integrate_ass_and_video_to_outdir(dest_f, mv, outdir)
                            if created:
                                print(f"Muxed -> {created}")
            continue

        if item.is_file():
            if item.suffix.lower() == ".srt":
                name = (item.stem + ".ass")
                outp = make_unique(name)
                convert(str(item), str(outp), force_align=force_align)
                adjust_ass_styles(str(outp), fontname="Arial", fontsize=18, force_align=force_align, margin_v=margin_v, raise_for_24=30, h_margin=h_margin, h_margin_pct=h_margin_pct, play_res_x=play_res_x, play_res_y=play_res_y, outline=outline, shadow=shadow)
                if mp4_list and mux:
                    mv = find_best_video_for_ass(outp, mp4_list)
                    if mv:
                        created = integrate_ass_and_video_to_outdir(outp, mv, outdir)
                        if created:
                            print(f"Muxed -> {created}")
                continue
            if item.suffix.lower() == ".ass":
                outp = make_unique(item.name)
                shutil.copy2(item, outp)
                adjust_ass_styles(str(outp), fontname="Arial", fontsize=18, force_align=force_align, margin_v=margin_v, raise_for_24=30, h_margin=h_margin, h_margin_pct=h_margin_pct, play_res_x=play_res_x, play_res_y=play_res_y, outline=outline, shadow=shadow)
                if mp4_list and mux:
                    mv = find_best_video_for_ass(outp, mp4_list)
                    if mv:
                        created = integrate_ass_and_video_to_outdir(outp, mv, outdir)
                        if created:
                            print(f"Muxed -> {created}")
                continue

            # treat as archive if matches
            if is_supported_archive(item):
                with tempfile.TemporaryDirectory() as td:
                    tdpath = Path(td)
                    try:
                        extract_archive(item, tdpath)
                    except Exception as e:
                        print(f"Failed to extract {item}: {e}", file=sys.stderr)
                        continue
                    for f in tdpath.rglob("*"):
                        if f.is_file() and f.suffix.lower() == ".srt":
                            name = f.relative_to(tdpath).with_suffix(".ass").name
                            outp = make_unique(name)
                            convert(str(f), str(outp), force_align=force_align)
                            adjust_ass_styles(str(outp), fontname="Arial", fontsize=18, force_align=force_align, margin_v=margin_v, raise_for_24=30, h_margin=h_margin, h_margin_pct=h_margin_pct, play_res_x=play_res_x, play_res_y=play_res_y, outline=outline, shadow=shadow)
                            if mp4_list and mux:
                                mv = find_best_video_for_ass(outp, mp4_list)
                                if mv:
                                    created = integrate_ass_and_video_to_outdir(outp, mv, outdir)
                                    if created:
                                        print(f"Muxed -> {created}")
                        elif f.is_file() and f.suffix.lower() == ".ass":
                            name = f.relative_to(tdpath).name
                            destp = make_unique(name)
                            shutil.copy2(f, destp)
                            adjust_ass_styles(str(destp), fontname="Arial", fontsize=18, force_align=force_align, margin_v=margin_v, raise_for_24=30, h_margin=h_margin, h_margin_pct=h_margin_pct, play_res_x=play_res_x, play_res_y=play_res_y, outline=outline, shadow=shadow)
                            if mp4_list and mux:
                                mv = find_best_video_for_ass(destp, mp4_list)
                                if mv:
                                    created = integrate_ass_and_video_to_outdir(destp, mv, outdir)
                                    if created:
                                        print(f"Muxed {created}")
                continue

            print(f"Skipping unsupported file: {item}")


def main():
    p = argparse.ArgumentParser(description="Batch extract & convert subtitles in sub/ to output/")
    p.add_argument("--subdir", default="sub", help="directory containing archives/files")
    p.add_argument("--outdir", default="output", help="output root directory")
    p.add_argument("--align", default="bottom-center", choices=["bottom-center", "bottom-left", "top-center"], help="force alignment for converted files")
    p.add_argument("--inputdir", default="input", help="root dir to search for mp4 video files (recursive)")
    p.add_argument("--mux", action="store_true", help="mux generated .ass into MKV next to video using ffmpeg")
    p.add_argument("--raise-by", type=int, default=40, help="raise subtitle vertical margin in pixels (increase MarginV). Default: 40")
    p.add_argument("--h-margin", type=int, default=8, help="horizontal margin (MarginL/MarginR) in pixels; lower value -> wider text area. Default: 8")
    p.add_argument("--h-margin-pct", type=int, default=0, help="horizontal margin percent reduction (0-100); e.g. 70 reduces margins by 70% to widen text area")
    p.add_argument("--play-res-x", type=int, default=1920, help="ASS PlayResX (horizontal resolution); larger value gives more width for subtitles. Default: 1920")
    p.add_argument("--play-res-y", type=int, default=1080, help="ASS PlayResY (vertical resolution); affects font scaling. Default: 1080")
    p.add_argument("--outline", type=float, default=0.5, help="outline width (0.0-2.0); smaller value = less shadow. Default: 0.5")
    p.add_argument("--shadow", type=float, default=0.5, help="shadow blur (0.0-2.0); smaller value = less shadow. Default: 0.5")

    args = p.parse_args()

    subdir = Path(args.subdir)
    outdir = Path(args.outdir)
    if not subdir.exists():
        print(f"subdir not found: {subdir}", file=sys.stderr)
        raise SystemExit(2)

    mp4_list = []
    inputdir = Path(args.inputdir)
    if inputdir.exists():
        mp4_list = [p for p in inputdir.rglob("*.mp4") if p.is_file()]
    else:
        print(f"inputdir not found: {inputdir} (continuing without video matching)")

    # use a temporary directory for all intermediate .ass files so they can be cleaned up easily
    with tempfile.TemporaryDirectory() as tdroot:
        temp_root = Path(tdroot)
        process_subdir(
            subdir,
            outdir,
            temp_root,
            force_align=args.align,
            mp4_list=mp4_list,
            mux=args.mux,
            margin_v=(args.raise_by if args.raise_by and args.raise_by > 0 else None),
            h_margin=(args.h_margin if args.h_margin and args.h_margin > 0 else None),
            h_margin_pct=(args.h_margin_pct if args.h_margin_pct and args.h_margin_pct > 0 else None),
            play_res_x=(args.play_res_x if args.play_res_x and args.play_res_x > 0 else None),
            play_res_y=(args.play_res_y if args.play_res_y and args.play_res_y > 0 else None),
            outline=(args.outline if args.outline and args.outline > 0 else None),
            shadow=(args.shadow if args.shadow and args.shadow > 0 else None),
        )

    if args.mux:
        print("Mux option enabled: will attempt to create MKV files with subtitles for matched videos.")

    # delete any .mkv files under inputdir as requested
    if inputdir.exists():
        for mk in inputdir.rglob("*.mkv"):
            try:
                mk.unlink()
                print(f"Deleted input MKV: {mk}")
            except Exception as e:
                print(f"Failed to delete {mk}: {e}")


if __name__ == "__main__":
    main()
