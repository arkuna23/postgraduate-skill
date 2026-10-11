#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENC = ROOT / "data" / "retest.json.enc"
def env_file():
    base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / "environment.d" / "postgraduate.conf"
FIELDS = """\
--school --college --major --major-code --direction --subject   文本包含
--tier --region --province --city --area --study-mode --year   精确匹配
--score   分数落在分段内，并给出 matchedSegment
--min-admit-rate --min-admitted --min-retest   分段阈值
--limit   默认 20
--count   只输出条数
--fields  打印本说明，不解密
"""


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(1)


def load_password():
    current = os.environ.get("POSTGRADUATE_DATA_KEY")
    if current:
        return current
    path = env_file()
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() != "POSTGRADUATE_DATA_KEY":
                continue
            value = value.strip().strip("\"'")
            if value:
                os.environ["POSTGRADUATE_DATA_KEY"] = value
                return value
    fail("没有密码。向用户要 POSTGRADUATE_DATA_KEY，写入 ~/.config/environment.d/postgraduate.conf。不要到 skill 目录里找。")


def decrypt():
    if not ENC.is_file():
        fail(f"没有密文 {ENC}")
    load_password()
    result = subprocess.run(
        [
            "openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000",
            "-pass", "env:POSTGRADUATE_DATA_KEY", "-in", str(ENC),
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        fail(result.stderr.decode("utf-8", "replace").strip() or "解密失败")
    return json.loads(result.stdout.decode("utf-8"))


def contains(value, needle):
    if not needle:
        return True
    if isinstance(value, list):
        return any(needle in str(item) for item in value)
    return needle in str(value or "")


def same(value, expected):
    if expected is None:
        return True
    return str(value or "") == str(expected)


def number(value):
    if value is None or value == "":
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def bounds(segment):
    found = [int(item) for item in re.findall(r"\d+", str(segment.get("range") or ""))]
    if len(found) >= 2:
        return found[0], found[1]
    begin = number(segment.get("beginScore"))
    step = number(segment.get("step"))
    if begin is None or step is None:
        return None
    start = int(begin)
    width = int(step)
    return start, start + width - 1 if width > 1 else start


def covers(segment, score):
    span = bounds(segment)
    return span is not None and span[0] <= score <= span[1]


def admit_rate(segment):
    return number(segment.get("admitRate")) or 0


def keep_segment(segment, args):
    if args.min_admit_rate is not None and admit_rate(segment) < args.min_admit_rate:
        return False
    admitted = number(segment.get("admitted"))
    retest = number(segment.get("retest"))
    if args.min_admitted is not None and (admitted is None or admitted < args.min_admitted):
        return False
    if args.min_retest is not None and (retest is None or retest < args.min_retest):
        return False
    return True

def has_subject(item, needle):
    if not needle:
        return True
    for subject in item.get("subjects") or []:
        if needle in str(subject.get("code") or "") or needle in str(subject.get("name") or ""):
            return True
    return False


def match_item(item, args):
    checks = [
        contains(item.get("school"), args.school),
        contains(item.get("college"), args.college),
        contains(item.get("major"), args.major),
        contains(item.get("majorCode"), args.major_code),
        contains(item.get("directions"), args.direction),
        has_subject(item, args.subject),
        same(item.get("tier"), args.tier),
        same(item.get("region"), args.region),
        same(item.get("province"), args.province),
        same(item.get("city"), args.city),
        same(item.get("area"), args.area),
        same(item.get("studyMode"), args.study_mode),
        same(item.get("year"), args.year),
    ]
    if not all(checks):
        return None
    segments = item.get("segments") or []
    if args.score is None and args.min_admit_rate is None and args.min_admitted is None and args.min_retest is None:
        return item
    pool = segments
    if args.score is not None:
        pool = [segment for segment in segments if covers(segment, args.score)]
    pool = [segment for segment in pool if keep_segment(segment, args)]
    if not pool:
        return None
    if args.score is None:
        return item
    chosen = sorted(pool, key=lambda segment: (admit_rate(segment), number(segment.get("admitted")) or 0), reverse=True)[0]
    matched = dict(item)
    matched["matchedSegment"] = chosen
    matched["sortRate"] = admit_rate(chosen)
    matched["sortAdmitted"] = number(chosen.get("admitted")) or 0
    return matched


def parser():
    parse = argparse.ArgumentParser(add_help=True)
    parse.add_argument("--school")
    parse.add_argument("--college")
    parse.add_argument("--major")
    parse.add_argument("--major-code")
    parse.add_argument("--direction")
    parse.add_argument("--subject")
    parse.add_argument("--tier")
    parse.add_argument("--region")
    parse.add_argument("--province")
    parse.add_argument("--city")
    parse.add_argument("--area")
    parse.add_argument("--study-mode")
    parse.add_argument("--year")
    parse.add_argument("--score", type=float)
    parse.add_argument("--min-admit-rate", type=float)
    parse.add_argument("--min-admitted", type=float)
    parse.add_argument("--min-retest", type=float)
    parse.add_argument("--limit", type=int, default=20)
    parse.add_argument("--count", action="store_true")
    parse.add_argument("--fields", action="store_true")
    return parse


def main():
    args = parser().parse_args()
    if args.fields:
        print(FIELDS, end="")
        return
    payload = decrypt()
    found = []
    for item in payload.get("items") or []:
        matched = match_item(item, args)
        if matched is not None:
            found.append(matched)
    if args.score is not None:
        found.sort(key=lambda item: (item.get("sortRate") or 0, item.get("sortAdmitted") or 0), reverse=True)
        for item in found:
            item.pop("sortRate", None)
            item.pop("sortAdmitted", None)
    if args.count:
        print(len(found))
        return
    print(json.dumps(found[: args.limit], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
