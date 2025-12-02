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
    extract_player_short_code,
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


class TestExtractPlayerShortCode(unittest.TestCase):
    """Test extract_player_short_code function"""

    @patch('app.routes.webhook.Player')
    def test_extract_short_code_basic(self, mock_player):
        """Test extracting short_code from content"""
        mock_player.find_by_short_code.return_value = {'name': 'Nguyễn Văn Mạnh', 'short_code': 'P001'}
        
        # Test with P001 pattern
        result = extract_player_short_code('Manh thanh toan cau long P001')
        mock_player.find_by_short_code.assert_called_with('P001')
        self.assertEqual(result['short_code'], 'P001')

    @patch('app.routes.webhook.Player')
    def test_extract_short_code_with_date(self, mock_player):
        """Test extracting short_code from content with date"""
        mock_player.find_by_short_code.return_value = {'name': 'Nguyễn Văn Mạnh', 'short_code': 'P001'}
        
        result = extract_player_short_code('Manh thanh toan cau long - 28122025 - P001')
        mock_player.find_by_short_code.assert_called_with('P001')
        self.assertIsNotNone(result)

    @patch('app.routes.webhook.Player')
    def test_extract_short_code_case_insensitive(self, mock_player):
        """Test case insensitivity for short_code"""
        mock_player.find_by_short_code.return_value = {'name': 'Test', 'short_code': 'P002'}
        
        # Test lowercase
        result = extract_player_short_code('manh thanh toan cau long p002')
        mock_player.find_by_short_code.assert_called_with('P002')
        self.assertIsNotNone(result)

    @patch('app.routes.webhook.Player')
    def test_extract_short_code_not_found(self, mock_player):
        """Test when short_code not found in database"""
        mock_player.find_by_short_code.return_value = None
        
        result = extract_player_short_code('Manh thanh toan cau long P999')
        self.assertIsNone(result)

    def test_extract_short_code_no_pattern(self):
        """Test when no short_code pattern in content"""
        result = extract_player_short_code('Manh thanh toan cau long')
        self.assertIsNone(result)

    def test_extract_short_code_empty_content(self):
        """Test with empty content"""
        self.assertIsNone(extract_player_short_code(''))
        self.assertIsNone(extract_player_short_code(None))


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
