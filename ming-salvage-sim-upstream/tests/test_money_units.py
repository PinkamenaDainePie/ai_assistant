import unittest

from ming_sim.simulation import _clean_economy_moves


class MoneyUnitTests(unittest.TestCase):
    def test_liang_amount_is_converted_to_fractional_wanliang(self):
        moves = _clean_economy_moves([
            {
                "账户": "国库",
                "增量": 200,
                "单位": "两",
                "分类": "赏银",
                "原因": "赏工匠二百两",
            }
        ])

        self.assertEqual(len(moves), 1)
        self.assertEqual(moves[0]["account"], "国库")
        self.assertAlmostEqual(moves[0]["delta"], 0.02)

    def test_wanliang_amount_stays_in_wanliang(self):
        moves = _clean_economy_moves([
            {
                "账户": "内库",
                "增量": -20,
                "分类": "赈灾",
                "原因": "内库拨银二十万两",
            }
        ])

        self.assertEqual(len(moves), 1)
        self.assertEqual(moves[0]["account"], "内库")
        self.assertEqual(moves[0]["delta"], -20)


if __name__ == "__main__":
    unittest.main()
