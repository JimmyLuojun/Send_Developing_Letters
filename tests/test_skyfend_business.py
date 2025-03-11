import unittest
import os
from src.data.skyfend_business import read_skyfend_business

class TestSkyfendBusiness(unittest.TestCase):

    def test_read_skyfend_business(self):
        # Path to the sample Word document
        sample_docx = os.path.join(
            os.path.dirname(__file__), 
            '../data/raw/test_main Business of Skyfend.docx'
        )
        
        # Read the business description from the document
        business_description = read_skyfend_business(sample_docx)
        
        # Print the business description for verification
        print("Business Description:", business_description)
        
        # Assertions to verify the output
        self.assertIsInstance(business_description, str)
        self.assertGreater(len(business_description), 0)
        self.assertIn("Skyfend", business_description)  # Example check for expected content

if __name__ == '__main__':
    unittest.main()
