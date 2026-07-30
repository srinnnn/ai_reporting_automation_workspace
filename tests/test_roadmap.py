from __future__ import annotations

import unittest
from datetime import date

from intranet_app.roadmap import DailyTask, ROADMAP_WEEKS, RoadmapWeek, daily_task_date, roadmap_day_count


class RoadmapTests(unittest.TestCase):
    def test_roadmap_has_ten_weeks_and_fifty_ordered_days(self) -> None:
        self.assertEqual(len(ROADMAP_WEEKS), 10)
        self.assertEqual(roadmap_day_count(), 50)
        self.assertEqual(ROADMAP_WEEKS[0].start_date, date(2026, 7, 27))
        self.assertEqual(ROADMAP_WEEKS[-1].end_date, date(2026, 10, 2))
        self.assertEqual(daily_task_date(ROADMAP_WEEKS[0], ROADMAP_WEEKS[0].tasks[4]), date(2026, 7, 31))

    def test_daily_task_rejects_empty_text_and_out_of_range_day(self) -> None:
        with self.assertRaises(ValueError):
            DailyTask(0, "任务", "业务", "开发", "交付", "验收")
        with self.assertRaises(ValueError):
            DailyTask(1, "", "业务", "开发", "交付", "验收")

    def test_week_rejects_missing_daily_tasks(self) -> None:
        task = DailyTask(1, "任务", "业务", "开发", "交付", "验收")
        with self.assertRaises(ValueError):
            RoadmapWeek(1, date(2026, 7, 27), date(2026, 7, 31), "数据处理", "目标", "依赖", "里程碑", (task,))

    def test_daily_task_date_rejects_invalid_types(self) -> None:
        with self.assertRaises(TypeError):
            daily_task_date("week", ROADMAP_WEEKS[0].tasks[0])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
