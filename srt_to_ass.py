#!/usr/bin/env python3
"""Convert SRT to ASS and add simple automatic positioning tags.

Usage:
  python3 srt_to_ass.py in.srt out.ass

Positioning rules (heuristic):
- If subtitle starts with a parenthesis or contains a full-width parenthesis -> top-center
- If subtitle looks like a speaker label (e.g. "NAME: text") -> bottom-left
- Otherwise -> bottom-center
"""
import argparse
import re
import sys

try:
    import pysubs2
except Exception as e:
    print("Missing dependency 'pysubs2'. Install with: python3 -m pip install pysubs2", file=sys.stderr)
    raise


def choose_tag(text: str, force_align: str | None = None) -> str:
    """Choose an override tag for a subtitle text.

    force_align: None or one of 'bottom-center', 'bottom-left', 'top-center'
    """
    if force_align is not None:
        if force_align == "bottom-center":
            return "{\\an2}"
        if force_align == "bottom-left":
            return "{\\an1}"
        if force_align == "top-center":
            return "{\\an8}"

    s = text.strip().replace("\n", " ")
    # top if starts with parentheses or has Chinese parentheses
    if re.match(r"^\s*[\(（]", s) or "（" in s:
        return "{\\an8}"  # top-center
    # speaker label like "NAME: ..." or "NAME：..."
    if re.match(r"^[^\n]{1,20}[:：]\s*", s):
        return "{\\an1}"  # bottom-left
    # default bottom-center
    return "{\\an2}"


def convert(infile: str, outfile: str, force_align: str | None = None) -> None:
    """Convert a single subtitle file (SRT/ASS input supported) to ASS.

    If force_align is provided, it overrides per-line heuristics. Valid values:
    'bottom-center', 'bottom-left', 'top-center', or None.
    """
    subs = pysubs2.load(infile, encoding="utf-8")
    for ev in subs:
        # skip if already has alignment override and not forcing
        if force_align is None and ev.text.startswith("{") and "\\an" in ev.text.split("}", 1)[0]:
            continue
        tag = choose_tag(ev.text, force_align=force_align)
        # remove any existing an override in the first override block
        if ev.text.startswith("{"):
            parts = ev.text.split("}", 1)
            head = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            # remove existing \anX in head
            head = re.sub(r"\\\\an\d", "", head)
            ev.text = head + "}" + tag + rest if head != "" else tag + rest
        else:
            ev.text = tag + ev.text
    subs.save(outfile, encoding="utf-8")


def adjust_ass_styles(filepath: str, fontname: str = "Arial", fontsize: int = 18, force_align: str | None = None, margin_v: int | None = None, raise_for_24: int | None = 20, h_margin: int | None = None, h_margin_pct: int | None = None, play_res_x: int | None = None, outline: float | None = None, shadow: float | None = None) -> None:
    """Adjust ASS styles (font name, size) and per-line alignment tags.

    - Updates all styles' `fontname` and `fontsize`.
    - Ensures each event has an alignment override that matches `force_align` (if provided).
    """
    subs = pysubs2.load(filepath, encoding="utf-8")
    # adjust PlayResX if requested (wider resolution -> more horizontal space for subtitles)
    if play_res_x is not None:
        try:
            subs.info["PlayResX"] = str(int(play_res_x))
        except Exception:
            pass
    # adjust outline and shadow if requested
    if outline is not None or shadow is not None:
        for style in subs.styles.values():
            try:
                if outline is not None:
                    style.outline = float(outline)
                if shadow is not None:
                    style.shadow = float(shadow)
            except Exception:
                pass
    # update styles
    # remember original horizontal margins so percent adjustments can reference them
    orig_hm: dict[str, int] = {}
    for style_name, style in list(subs.styles.items()):
        try:
            orig_hm[style_name] = int(style.marginl)
        except Exception:
            orig_hm[style_name] = 10
        style.fontname = fontname
        style.fontsize = float(fontsize)
        # alignment in styles: 1=bottom-left,2=bottom-center,8=top-center
        if force_align == "bottom-left":
            style.alignment = 1
        elif force_align == "bottom-center":
            style.alignment = 2
        elif force_align == "top-center":
            style.alignment = 8
        # adjust vertical margin if requested (MarginV in ASS)
        try:
            base_margin = int(margin_v) if margin_v is not None else 0
        except Exception:
            base_margin = 0
        # if this style uses fontsize ~24, apply an extra raise to avoid overlapping embedded subtitles
        try:
            style_fs = int(round(float(style.fontsize)))
        except Exception:
            style_fs = None
        extra = 0
        if style_fs == 24 and raise_for_24:
            extra = int(raise_for_24)
        try:
            style.marginv = base_margin + extra
        except Exception:
            pass
        # adjust horizontal margins if requested (MarginL/MarginR in ASS)
        if h_margin is not None:
            try:
                style.marginl = int(h_margin)
                style.marginr = int(h_margin)
            except Exception:
                pass
        elif h_margin_pct is not None:
            # reduce margins by percentage to widen usable area
            try:
                orig = orig_hm.get(style_name, 10)
                newm = max(0, int(orig * max(0.0, 1.0 - float(h_margin_pct) / 100.0)))
                style.marginl = newm
                style.marginr = newm
            except Exception:
                pass
        subs.styles[style_name] = style

    # update events: remove existing \an in first override and insert desired tag
    for ev in subs:
        # remove existing \an in first override block
        if ev.text.startswith("{"):
            parts = ev.text.split("}", 1)
            head = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            head = re.sub(r"\\an\d", "", head)
            ev.text = head + "}" + rest if head != "" else rest
        # insert new align tag if requested
        if force_align is not None:
            tag = choose_tag(ev.text, force_align=force_align)
            # avoid duplicating if already has tag at start
            if not ev.text.startswith(tag):
                ev.text = tag + ev.text
        # set per-event margins based on the event's style (respect raise_for_24 and h_margin)
        try:
            base_margin_ev = int(margin_v) if margin_v is not None else 0
        except Exception:
            base_margin_ev = 0
        ev_style = subs.styles.get(ev.style) if hasattr(ev, "style") else None
        extra_ev = 0
        try:
            if ev_style is not None and int(round(float(ev_style.fontsize))) == 24 and raise_for_24:
                extra_ev = int(raise_for_24)
        except Exception:
            extra_ev = 0
        try:
            ev.marginv = base_margin_ev + extra_ev
        except Exception:
            pass
        if h_margin is not None:
            try:
                ev.marginl = int(h_margin)
                ev.marginr = int(h_margin)
            except Exception:
                pass
        elif h_margin_pct is not None:
            try:
                base = 10
                if ev.style and ev.style in orig_hm:
                    base = orig_hm.get(ev.style, base)
                newme = max(0, int(base * max(0.0, 1.0 - float(h_margin_pct) / 100.0)))
                ev.marginl = newme
                ev.marginr = newme
            except Exception:
                pass

    subs.save(filepath, encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Convert SRT to ASS with simple automatic positioning")
    p.add_argument("infile")
    p.add_argument("outfile")
    args = p.parse_args()
    convert(args.infile, args.outfile)


if __name__ == "__main__":
    main()
