import datetime

from paissadb.calc import DEVALUE_TIME_NAIVE, earliest_possible_open_time, num_missed_devals

# *theoretically* these tests are fragile if devalue falls on a midnight locally
# or you happen to run these tests exactly at midnight

ONE_SECOND = datetime.timedelta(seconds=1)
ONE_HOUR = datetime.timedelta(hours=1)
ONE_HOUR_AND_A_BIT = ONE_HOUR + ONE_SECOND
ONE_DAY = datetime.timedelta(days=1)
TODAY = datetime.date.today()
TODAYS_DEVALUE = datetime.datetime.combine(TODAY, DEVALUE_TIME_NAIVE)
SOON_AFTER_DEVALUE_TIME = TODAYS_DEVALUE + ONE_SECOND
SOON_BEFORE_DEVALUE_TIME = TODAYS_DEVALUE - ONE_SECOND


# ============= devals =============
class TestDevals:
    def test_num_missed_devals_0_after_deval(self):
        # ==== known soon after devalue ====
        known_at = SOON_AFTER_DEVALUE_TIME
        # hours 0-23: devalue 0
        for h in range(24):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=0, known_at=known_at, when=when) == 0

        # hours 24-29: devalue 1
        for h in range(24, 30):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=0, known_at=known_at, when=when) == 1

        # hours 30-35: devalue 2
        for h in range(30, 36):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=0, known_at=known_at, when=when) == 2

    def test_num_missed_devals_0_before_deval(self):
        # ==== known soon before devalue ====
        known_at = SOON_BEFORE_DEVALUE_TIME
        # hour 0: devalue 0
        assert num_missed_devals(num_devals=0, known_at=known_at, when=SOON_BEFORE_DEVALUE_TIME) == 0
        assert num_missed_devals(num_devals=0, known_at=known_at, when=SOON_AFTER_DEVALUE_TIME) == 1

        # hours 1-6: devalue 1
        for h in range(1, 7):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=0, known_at=known_at, when=when) == 1

        # hours 7-12: devalue 2
        for h in range(7, 12):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=0, known_at=known_at, when=when) == 2

    def test_num_missed_devals_0_between_devals(self):
        # ==== known halfway-ish between devalues ====
        known_at = SOON_AFTER_DEVALUE_TIME + ONE_HOUR_AND_A_BIT * 12
        # hours 0-11: devalue 0
        for h in range(12):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=0, known_at=known_at, when=when) == 0

        # hours 12-17: devalue 1
        for h in range(12, 18):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=0, known_at=known_at, when=when) == 1

        # hours 18-23: devalue 2
        for h in range(18, 24):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=0, known_at=known_at, when=when) == 2

    def test_num_missed_devals_some_after_deval(self):
        # ==== known immediately after deval ====
        known_at = SOON_AFTER_DEVALUE_TIME
        # hours 0-5: devalue 1 (0 missed)
        for h in range(6):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=1, known_at=known_at, when=when) == 0

        # hours 6-11: devalue 2 (1 missed)
        for h in range(6, 12):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=1, known_at=known_at, when=when) == 1

        # hours 12-17: devalue 3 (2 missed)
        for h in range(12, 18):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=1, known_at=known_at, when=when) == 2

    def test_num_missed_devals_some_before_deval(self):
        # ==== known immediately before deval ====
        known_at = SOON_BEFORE_DEVALUE_TIME
        # hour 0: devalue 1 (0 missed)
        assert num_missed_devals(num_devals=1, known_at=known_at, when=SOON_BEFORE_DEVALUE_TIME) == 0
        assert num_missed_devals(num_devals=1, known_at=known_at, when=SOON_AFTER_DEVALUE_TIME) == 1

        # hours 1-6: devalue 2 (1 missed)
        for h in range(1, 7):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=1, known_at=known_at, when=when) == 1

        # hours 7-12: devalue 3 (2 missed)
        for h in range(7, 12):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=1, known_at=known_at, when=when) == 2

    def test_num_missed_devals_some_between_devals(self):
        # ==== known halfway-ish between devalues ====
        known_at = SOON_AFTER_DEVALUE_TIME + ONE_HOUR_AND_A_BIT * 3
        # hours 0-2: devalue 1 (0 missed)
        for h in range(3):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=1, known_at=known_at, when=when) == 0

        # hours 3-8: devalue 2 (1 missed)
        for h in range(3, 8):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=1, known_at=known_at, when=when) == 1

        # hours 9-14: devalue 3 (1 missed)
        for h in range(9, 14):
            when = known_at + ONE_HOUR * h
            assert num_missed_devals(num_devals=1, known_at=known_at, when=when) == 2


# ============= open time =============
def test_earliest_open_time():
    assert earliest_possible_open_time(num_devals=0, known_at=SOON_AFTER_DEVALUE_TIME) == TODAYS_DEVALUE
    assert earliest_possible_open_time(num_devals=0, known_at=SOON_BEFORE_DEVALUE_TIME) == TODAYS_DEVALUE - ONE_DAY
    assert earliest_possible_open_time(num_devals=1, known_at=SOON_AFTER_DEVALUE_TIME) == TODAYS_DEVALUE - ONE_DAY
    assert earliest_possible_open_time(num_devals=1, known_at=SOON_BEFORE_DEVALUE_TIME) == TODAYS_DEVALUE - ONE_DAY


def test_earliest_open_time_spanning_day():
    # now: 2021-04-22 1:32 (reset + 8h32m)
    # num devals: 2
    # t0: 2021-04-21 13:32
    # devalue time: 17:00
    # should be earliest: 2021-4-20 17:00
    k1 = datetime.datetime(year=2021, month=4, day=22, hour=1, minute=32)
    d1 = datetime.time(hour=17)
    s1 = datetime.datetime(year=2021, month=4, day=20, hour=17)
    assert earliest_possible_open_time(num_devals=2, known_at=k1, devalue_time=d1) == s1

    # now: 2021-01-02 9:00 (reset + 23h)
    # num devals: 4
    # t0: 2021-01-01 9:00
    # devalue time: 10:00
    # should be earliest: 2020-12-31 10:00
    k2 = datetime.datetime(year=2021, month=1, day=2, hour=9)
    d2 = datetime.time(hour=10)
    s2 = datetime.datetime(year=2020, month=12, day=31, hour=10)
    assert earliest_possible_open_time(num_devals=4, known_at=k2, devalue_time=d2) == s2
