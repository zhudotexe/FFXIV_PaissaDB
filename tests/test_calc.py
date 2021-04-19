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
