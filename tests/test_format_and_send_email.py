# test_format_and_send_email.py  

import unittest
from src.utils.format_and_send_email import format_email_subject, format_email_body


class TestEmailFormatter(unittest.TestCase):

    def setUp(self):
        self.subject = "Skyfend Partnership"
        self.body = "We would like to collaborate with you."

    def test_format_email_subject(self):
        expected = "Cooperation Opportunity: Skyfend Partnership"
        result = format_email_subject(self.subject)
        self.assertEqual(result, expected)

    def test_format_email_subject_empty(self):
        expected = "Cooperation Opportunity: "
        result = format_email_subject("")
        self.assertEqual(result, expected)

    def test_format_email_body(self):
        expected = ("Dear Sir/Madam,\n\n"
                    "We would like to collaborate with you.\n\n"
                    "Best regards,\nYour Company")
        result = format_email_body(self.body)
        self.assertEqual(result, expected)

    def test_format_email_body_empty(self):
        expected = "Dear Sir/Madam,\n\n\n\nBest regards,\nYour Company"
        result = format_email_body("")
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()
