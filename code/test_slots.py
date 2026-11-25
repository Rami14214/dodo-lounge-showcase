from datetime import date, datetime, time

from app.data import TZ
from app.slots import available_starts, booking_window

MON = date(2026, 11, 16)
SUN = date(2026, 11, 15)
SAT = date(2026, 11, 21)
EARLY = datetime(2026, 11, 1, 9, 0, tzinfo=TZ)


def dt(d, h, m=0):
    return datetime.combine(d, time(h, m), TZ)


def test_fixed_slots_empty_day():
    got = available_starts("megabase", "dodo", MON, [], EARLY)
    assert got == [time(8), time(9, 40), time(11, 15), time(13), time(14, 40), time(16, 15)]


def test_polygel_allows_0730():
    assert available_starts("polygel", "dodo", MON, [], EARLY) == [time(7, 30), time(14)]


def test_polygel_blocks_megabase_for_same_staff():
    busy = [booking_window("polygel", dt(MON, 7, 30))]
    got = available_starts("megabase", "dodo", MON, busy, EARLY)
    assert time(8) not in got and time(9, 40) not in got and time(11, 15) in got


def test_megabase_blocks_polygel_overlap():
    busy = [booking_window("megabase", dt(MON, 14, 40))]
    assert available_starts("polygel", "dodo", MON, busy, EARLY) == [time(7, 30)]


def test_sunday_closed():
    assert available_starts("megabase", "dodo", SUN, [], EARLY) == []


def test_past_times_hidden_today():
    now = datetime(2026, 11, 16, 10, 0, tzinfo=TZ)
    assert available_starts("megabase", "dodo", MON, [], now)[0] == time(11, 15)


WEEK = [time(8), time(9, 40), time(11, 15), time(13), time(14, 40), time(16, 15)]


def test_weekday_pedicures_use_the_set_times():
    for svc in ("pedi-polish", "pedi-gel", "pedi-russian"):
        assert available_starts(svc, "jana", MON, [], EARLY) == WEEK
    assert available_starts("pedi-medical", "dodo", MON, [], EARLY) == WEEK


def test_medical_pedicure_is_dodo_only():
    assert available_starts("pedi-medical", "jana", MON, [], EARLY) == []
    assert available_starts("pedi-medical", "sarah", MON, [], EARLY) == []
    assert available_starts("pedi-medical", "dodo", SAT, [], EARLY)[0] == time(7, 30)


def test_sarah_weekdays_only_940_and_1115():
    assert available_starts("pedi-gel", "sarah", MON, [], EARLY) == [time(9, 40), time(11, 15)]
    busy = [booking_window("pedi-gel", dt(MON, 9, 40))]
    assert available_starts("pedi-polish", "sarah", MON, busy, EARLY) == [time(11, 15)]
    # Saturday she follows the normal times, like Jana
    assert available_starts("pedi-gel", "sarah", SAT, [], EARLY) == available_starts("pedi-gel", "jana", SAT, [], EARLY)


def test_pedicure_overlap():
    busy = [booking_window("pedi-gel", dt(MON, 10))]  # 10:00-11:30
    got = available_starts("pedi-gel", "jana", MON, busy, EARLY)
    assert time(9, 40) not in got and time(11, 15) not in got and time(8) in got


def test_jana_lunch_1pm_booked_closes_415():
    busy = [booking_window("megabase-jana", dt(MON, 13))]
    got = available_starts("megabase-jana", "jana", MON, busy, EARLY)
    assert time(16, 15) not in got and time(14, 40) in got
    assert time(16, 15) not in available_starts("pedi-gel", "jana", MON, busy, EARLY)
    assert available_starts("polygel-jana", "jana", MON, busy, EARLY) == [time(7, 30)]


def test_jana_lunch_415_booked_closes_1pm():
    busy = [booking_window("pedi-polish", dt(MON, 16, 15))]
    got = available_starts("megabase-jana", "jana", MON, busy, EARLY)
    assert time(13) not in got and time(14, 40) in got
    assert time(14) not in available_starts("polygel-jana", "jana", MON, busy, EARLY)  # 2:00-4:30 hits 4:15


def test_jana_polygel_at_2pm_puts_lunch_at_1pm():
    assert time(14) in available_starts("polygel-jana", "jana", MON, [], EARLY)
    busy = [booking_window("polygel-jana", dt(MON, 14))]
    got = available_starts("megabase-jana", "jana", MON, busy, EARLY)
    assert time(13) not in got and time(11, 15) in got


def test_jana_lunch_rule_weekdays_only_and_not_for_dodo():
    busy = [booking_window("megabase-jana", dt(SAT, 12, 30))]
    assert time(14) in available_starts("megabase-jana", "jana", SAT, busy, EARLY)
    busy = [booking_window("megabase", dt(MON, 13))]
    assert time(16, 15) in available_starts("megabase", "dodo", MON, busy, EARLY)


def test_invalid_staff_for_service():
    assert available_starts("pedi-gel", "dodo", MON, [], EARLY) == []
    assert available_starts("megabase", "sarah", MON, [], EARLY) == []


def test_no_end_date_book_years_ahead():
    far = date(2031, 11, 17)  # a Monday, 5 years out
    assert available_starts("megabase", "dodo", far, [], EARLY)[0] == time(8)
    assert available_starts("megabase", "dodo", date(2031, 11, 16), [], EARLY) == []  # Sunday still closed
    assert available_starts("megabase", "dodo", date(2026, 10, 26), [], EARLY) == []  # past day still blocked


def test_december_2026_fully_booked_for_clients():
    # Dodo's paper book is full for December: no website slots, January opens again
    assert available_starts("megabase", "dodo", date(2026, 12, 1), [], EARLY) == []
    assert available_starts("pedi-gel", "sarah", date(2026, 12, 31), [], EARLY) == []
    assert available_starts("megabase", "dodo", date(2026, 11, 30), [], EARLY)[0] == time(8)
    assert available_starts("megabase", "dodo", date(2027, 1, 2), [], EARLY)[0] == time(7, 30)  # a Saturday



def test_saturday_last_start_is_3pm():
    assert available_starts("megabase", "dodo", SAT, [], EARLY) == [
        time(7, 30), time(9), time(10, 45), time(12, 30), time(14)]
    assert available_starts("polygel", "dodo", SAT, [], EARLY) == [time(7, 30), time(14)]
    assert available_starts("pedi-polish", "sarah", SAT, [], EARLY) == [
        time(7, 30), time(8, 45), time(10), time(11, 15), time(12, 30), time(13, 45), time(15)]
    assert available_starts("pedi-gel", "sarah", SAT, [], EARLY) == [
        time(7, 30), time(9), time(10, 30), time(12), time(13, 30), time(15)]
