import unittest

from it_news.cli import resolve_count


class ResolveCountTest(unittest.TestCase):
    def test_reads_the_given_env_name_and_default(self):
        self.assertEqual(resolve_count(None, {}, count_env="SECURITY_ARTICLES_PER_RUN", default=3), 3)
        self.assertEqual(resolve_count(None, {"SECURITY_ARTICLES_PER_RUN": "7"}, count_env="SECURITY_ARTICLES_PER_RUN", default=3), 7)
        self.assertEqual(resolve_count(None, {"IT_ARTICLES_PER_RUN": "7"}, count_env="SECURITY_ARTICLES_PER_RUN", default=3), 3)

    def test_clamps_and_ignores_invalid_values(self):
        self.assertEqual(resolve_count(None, {"X": "0"}, count_env="X", default=3), 1)
        self.assertEqual(resolve_count(None, {"X": "abc"}, count_env="X", default=3), 3)
        self.assertEqual(resolve_count(99, {}, count_env="X", default=3), 10)


if __name__ == "__main__":
    unittest.main()
