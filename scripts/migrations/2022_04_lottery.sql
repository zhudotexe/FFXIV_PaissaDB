-- lottery
-- Apr 16, 2022
-- Updates the following enums:
-- EventType.LOTTERY_INFO = "LOTTERY_INFO"
--
-- Adds the following columns:
-- plot_states.lotto_phase = Column(Integer, nullable=True)
-- plot_states.lotto_phase_until = Column(Integer, nullable=True)

ALTER TYPE EventType ADD VALUE 'LOTTERY_INFO';

ALTER TABLE plot_states
    ADD COLUMN lotto_phase INTEGER,
    ADD COLUMN lotto_phase_until INTEGER;
