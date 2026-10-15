from datetime import date

import pytest

from hrm.timeutil import TimeError, build_range, find_overlaps, op_day_of, parse_dt, validate_range
from hrm.services.importer import parse_line, split_events


def test_build_range_cross_midnight():
    s, e, crossed = build_range("2026-10-31", "20:00", "08:00")
    assert (s, e, crossed) == ("2026-10-31T20:00:00+07:00", "2026-11-01T08:00:00+07:00", True)


def test_op_day_boundaries():
    assert op_day_of(parse_dt("2026-10-16T07:59:00+07:00")) == date(2026, 10, 15)
    assert op_day_of(parse_dt("2026-10-16T08:00:00+07:00")) == date(2026, 10, 16)
    assert op_day_of(parse_dt("2026-10-16T01:00:00+00:00")) == date(2026, 10, 16)   # 08:00 Bangkok


def test_validate_range():
    with pytest.raises(TimeError):
        validate_range("2026-10-15T10:00:00+07:00", "2026-10-15T10:00:00+07:00")
    with pytest.raises(TimeError):
        validate_range("2026-10-15T10:00:00+07:00", None)
    validate_range(None, None)


def test_overlap_warning():
    es = [{"uid": "a", "start_at": "2026-10-15T09:00:00+07:00", "end_at": "2026-10-15T11:00:00+07:00"},
          {"uid": "b", "start_at": "2026-10-15T10:30:00+07:00", "end_at": "2026-10-15T12:00:00+07:00"},
          {"uid": "c", "start_at": "2026-10-15T12:00:00+07:00", "end_at": "2026-10-15T13:00:00+07:00"}]
    assert find_overlaps(es) == [("a", "b")]


@pytest.mark.parametrize("line,exp", [
    ("13:15-15:00 ติดตาม trouble", ("13:15", "15:00")),
    ("13.00 - 16.00 ประชุมติดตาม", ("13:00", "16:00")),
    ("13:15 - 16.00 น. ติดตาม", ("13:15", "16:00")),
    ("13:00-14:00'ตรวจสอบ", ("13:00", "14:00")),
    ("'11:00-11:30 'Safety Patrol", ("11:00", "11:30")),
    ("ทบทวนมาตรการ Crane", None),
    ("25:00-26:00 bad", None),
])
def test_parse_line(line, exp):
    assert parse_line(line)["time"] == exp


def test_split_events_continuation():
    ev = split_events("14.00-15.00 #1\nProduction follow meeting")
    assert len(ev) == 1 and ev[0]["title"] == "#1 Production follow meeting"
    ev = split_events("อบรม PPAP\nTong / Sai")
    assert len(ev) == 1 and ev[0]["time"] is None
