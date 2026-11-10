import os
import tempfile
import unittest

from app.database import db
from app.errors import AuthError


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "sub", "t.db")  # parent dir is created on demand

    def tearDown(self):
        self.tmp.cleanup()

    def test_register_and_login(self):
        uid = db.create_user("  Alice ", "correct horse", self.path)
        self.assertEqual(db.authenticate("ALICE", "correct horse", self.path),
                         {"id": uid, "username": "alice"})

    def test_wrong_password_and_unknown_user(self):
        db.create_user("bob", "password123", self.path)
        self.assertIsNone(db.authenticate("bob", "wrong-pass", self.path))
        self.assertIsNone(db.authenticate("nobody", "password123", self.path))
        self.assertIsNone(db.authenticate("bob", "", self.path))

    def test_duplicate_username(self):
        db.create_user("carol", "password123", self.path)
        with self.assertRaises(AuthError):
            db.create_user("Carol", "another-pass1", self.path)

    def test_validation(self):
        for name, pw in [("ab", "password123"), ("bad name!", "password123"),
                         ("x" * 40, "password123"), ("okname", "short"), ("okname", None)]:
            with self.assertRaises(AuthError, msg=(name, pw)):
                db.create_user(name, pw, self.path)

    def test_password_is_salted_and_not_stored_plain(self):
        a, b = db.hash_password("same-password"), db.hash_password("same-password")
        self.assertNotEqual(a, b)
        self.assertNotIn("same-password", a)
        self.assertTrue(db.verify_password("same-password", a))
        self.assertFalse(db.verify_password("other", a))
        self.assertFalse(db.verify_password("x", "garbage"))

    def test_quiz_history_round_trip_and_isolation(self):
        u1 = db.create_user("user1", "password123", self.path)
        u2 = db.create_user("user2", "password123", self.path)
        details = [{"question": "q", "correct": True}]
        db.save_quiz_attempt(u1, "Bonds", "easy", 3, 5, details, self.path)
        db.save_quiz_attempt(u1, "Options", "hard", 5, 5, details, self.path)
        db.save_quiz_attempt(u2, "Other", "easy", 1, 5, details, self.path)

        hist = db.get_quiz_history(u1, path=self.path)
        self.assertEqual([h["topic"] for h in hist], ["Options", "Bonds"])  # newest first
        self.assertEqual(hist[0]["details"], details)
        self.assertEqual(len(db.get_quiz_history(u2, path=self.path)), 1)
        self.assertEqual(db.get_user_stats(u1, self.path), {"attempts": 2, "average_pct": 80.0})
        self.assertEqual(db.get_user_stats(u2, self.path)["average_pct"], 20.0)

    def test_stats_for_user_without_attempts(self):
        uid = db.create_user("newbie", "password123", self.path)
        self.assertEqual(db.get_user_stats(uid, self.path), {"attempts": 0, "average_pct": 0.0})

    def test_attempt_for_missing_user_rejected(self):
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            db.save_quiz_attempt(999, "t", "easy", 1, 1, [], self.path)


if __name__ == "__main__":
    unittest.main()
