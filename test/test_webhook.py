#!/usr/bin/env python3
"""Test Sepay Webhook functionality"""

import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys

# Set up environment variables for testing
os.environ['MONGODB_URI'] = 'mongodb://localhost:27017'
os.environ['MONGODB_DB'] = 'badminton_tracker_test'
os.environ['SEPAY_API_KEY'] = 'test-api-key'

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.webhook import (
    extract_player_name,
    is_valid_payment_content,
    PAYMENT_KEYWORDS
)


class TestWebhookFunctions(unittest.TestCase):
    """Test webhook helper functions"""

    def test_payment_keywords(self):
        """Test that required keywords are defined"""
        self.assertIn('cau long', PAYMENT_KEYWORDS)
        self.assertIn('caulong', PAYMENT_KEYWORDS)
        self.assertIn('badminton', PAYMENT_KEYWORDS)
        self.assertIn('cl', PAYMENT_KEYWORDS)

    def test_is_valid_payment_content(self):
        """Test payment content validation"""
        # Valid contents
        self.assertTrue(is_valid_payment_content('Manh thanh toan cau long'))
        self.assertTrue(is_valid_payment_content('Manh thanh toan caulong'))
        self.assertTrue(is_valid_payment_content('Manh thanh toan badminton'))
        self.assertTrue(is_valid_payment_content('Manh thanh toan cl'))
        self.assertTrue(is_valid_payment_content('MANH THANH TOAN CAU LONG'))  # Case insensitive
        
        # Invalid contents
        self.assertFalse(is_valid_payment_content(''))
        self.assertFalse(is_valid_payment_content(None))
        self.assertFalse(is_valid_payment_content('Random content'))
        self.assertFalse(is_valid_payment_content('Manh thanh toan tennis'))

    def test_extract_player_name_cau_long(self):
        """Test extracting player name with 'cau long' keyword"""
        # Basic case
        self.assertEqual(extract_player_name('Manh thanh toan cau long'), 'Manh')
        
        # With common phrases
        self.assertEqual(extract_player_name('Manh cau long'), 'Manh')
        
        # Multiple words
        self.assertEqual(extract_player_name('Nguyen Van A thanh toan cau long'), 'Nguyen Van A')

    def test_extract_player_name_caulong(self):
        """Test extracting player name with 'caulong' keyword"""
        self.assertEqual(extract_player_name('Manh caulong'), 'Manh')
        self.assertEqual(extract_player_name('Manh thanh toan caulong'), 'Manh')

    def test_extract_player_name_badminton(self):
        """Test extracting player name with 'badminton' keyword"""
        self.assertEqual(extract_player_name('Manh badminton'), 'Manh')
        self.assertEqual(extract_player_name('Manh thanh toan badminton'), 'Manh')

    def test_extract_player_name_cl(self):
        """Test extracting player name with 'cl' keyword"""
        self.assertEqual(extract_player_name('Manh cl'), 'Manh')
        self.assertEqual(extract_player_name('Manh thanh toan cl'), 'Manh')

    def test_extract_player_name_case_insensitive(self):
        """Test case insensitivity"""
        self.assertEqual(extract_player_name('MANH CAU LONG'), 'MANH')
        self.assertEqual(extract_player_name('manh Cau Long'), 'manh')

    def test_extract_player_name_edge_cases(self):
        """Test edge cases"""
        # Empty content
        self.assertIsNone(extract_player_name(''))
        self.assertIsNone(extract_player_name(None))
        
        # Keyword at start (no name before it)
        self.assertIsNone(extract_player_name('cau long'))
        
        # Only spaces before keyword
        result = extract_player_name('   cau long')
        self.assertTrue(result is None or result == '')

    def test_extract_player_name_removes_common_phrases(self):
        """Test that common payment phrases are removed"""
        # 'thanh toan' should be removed
        result = extract_player_name('Manh thanh toan cau long')
        self.assertEqual(result, 'Manh')
        
        # 'tt' (abbreviation) should be removed
        result = extract_player_name('Manh tt cau long')
        self.assertEqual(result, 'Manh')


class TestTransactionModel(unittest.TestCase):
    """Test Transaction model"""

    def test_transaction_import(self):
        """Test that Transaction model can be imported"""
        from app.models.transaction import Transaction
        self.assertIsNotNone(Transaction)

    def test_transaction_fields(self):
        """Test Transaction model fields"""
        from app.models.transaction import Transaction
        
        # Check that the class has necessary methods
        self.assertTrue(hasattr(Transaction, 'find_by_sepay_id'))
        self.assertTrue(hasattr(Transaction, 'find_by_reference_code'))
        self.assertTrue(hasattr(Transaction, 'find_recent_by_player'))
        self.assertTrue(hasattr(Transaction, 'create'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
