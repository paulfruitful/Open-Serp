#!/usr/bin/env python3
"""
Unit and Integration Test Suite for Flask Direct Inferencing API
"""

import unittest
import json
import os
import tempfile
import csv

from app import app, build_platform_dork, load_seen_emails, save_new_emails, delete_emails_from_db, clear_all_emails

class FlaskAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Create a temporary CSV file for testing database endpoints
        self.temp_csv = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
        writer = csv.writer(self.temp_csv)
        writer.writerow(["existing1@example.com"])
        writer.writerow(["existing2@example.com"])
        self.temp_csv.close()
        self.temp_csv_path = self.temp_csv.name

    def tearDown(self):
        if os.path.exists(self.temp_csv_path):
            os.remove(self.temp_csv_path)

    def test_health_check(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("database", data)
        self.assertIn("platforms_supported", data)

    def test_get_platforms(self):
        response = self.client.get('/api/platforms')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get("success"))
        self.assertIn("instagram", data.get("platforms", {}))
        self.assertIn("linkedin", data.get("platforms", {}))
        self.assertIn("twitter", data.get("platforms", {}))

    def test_extract_text_direct(self):
        sample_text = "Reach our support team at support@test.com or founders on ceo (at) startup.io and info [at] domain.org"
        response = self.client.post(
            '/api/extract/text',
            data=json.dumps({"text": sample_text}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("count"), 3)
        self.assertIn("support@test.com", data.get("emails"))
        self.assertIn("ceo@startup.io", data.get("emails"))
        self.assertIn("info@domain.org", data.get("emails"))

    def test_extract_text_empty(self):
        response = self.client.post(
            '/api/extract/text',
            data=json.dumps({"text": ""}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data.get("success"))

    def test_extract_results(self):
        sample_results = [
            {
                "title": "Jane Doe - Graphic Designer",
                "link": "https://instagram.com/janedoe",
                "snippet": "Freelance designer. For business: jane.designs@gmail.com"
            },
            {
                "title": "Agency Portfolios",
                "link": "https://twitter.com/agency",
                "snippet": "Contact us at contact@agency.io or jane.designs@gmail.com"
            }
        ]
        response = self.client.post(
            '/api/extract/results',
            data=json.dumps({"results": sample_results}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("count"), 2)
        emails = data.get("emails")
        self.assertIn("jane.designs@gmail.com", emails)
        self.assertIn("contact@agency.io", emails)
        # Verify source mapping has multiple URLs for jane
        self.assertEqual(len(emails["jane.designs@gmail.com"]), 2)

    def test_platform_dork_builder(self):
        dork = build_platform_dork("instagram", "fitness coach")
        self.assertIn("site:instagram.com", dork)
        self.assertIn('"fitness coach"', dork)
        self.assertIn('"@gmail.com"', dork)

    def test_leads_database_crud(self):
        # 1. GET leads from temp CSV
        response = self.client.get(f'/api/leads?csv_path={self.temp_csv_path}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("total"), 2)
        self.assertIn("existing1@example.com", data.get("leads"))

        # 2. POST add new lead
        add_response = self.client.post(
            '/api/leads',
            data=json.dumps({
                "emails": ["newlead1@test.com", "existing1@example.com"],
                "csv_path": self.temp_csv_path
            }),
            content_type='application/json'
        )
        self.assertEqual(add_response.status_code, 200)
        add_data = json.loads(add_response.data)
        self.assertTrue(add_data.get("success"))
        self.assertEqual(add_data.get("added_count"), 1)  # Only 1 is new
        self.assertEqual(add_data.get("database_total"), 3)

        # 3. Search filter
        search_res = self.client.get(f'/api/leads?csv_path={self.temp_csv_path}&q=newlead1')
        search_data = json.loads(search_res.data)
        self.assertEqual(search_data.get("total"), 1)
        self.assertEqual(search_data.get("leads")[0], "newlead1@test.com")

        # 4. DELETE single lead
        del_response = self.client.delete(
            '/api/leads',
            data=json.dumps({
                "email": "newlead1@test.com",
                "csv_path": self.temp_csv_path
            }),
            content_type='application/json'
        )
        self.assertEqual(del_response.status_code, 200)
        del_data = json.loads(del_response.data)
        self.assertTrue(del_data.get("success"))
        self.assertEqual(del_data.get("removed_count"), 1)
        self.assertEqual(del_data.get("database_total"), 2)

        # 5. Clear all
        clear_res = self.client.delete(
            '/api/leads',
            data=json.dumps({
                "clear_all": True,
                "csv_path": self.temp_csv_path
            }),
            content_type='application/json'
        )
        self.assertEqual(clear_res.status_code, 200)
        clear_data = json.loads(clear_res.data)
        self.assertEqual(clear_data.get("database_total"), 0)

    def test_export_leads(self):
        response = self.client.get(f'/api/leads/export?csv_path={self.temp_csv_path}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Type"), "text/csv; charset=utf-8")

        json_response = self.client.get(f'/api/leads/export?csv_path={self.temp_csv_path}&format=json')
        self.assertEqual(json_response.status_code, 200)
        data = json.loads(json_response.data)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("total"), 2)

    def test_docs_and_dashboard(self):
        docs_res = self.client.get('/api/docs')
        self.assertEqual(docs_res.status_code, 200)
        docs_data = json.loads(docs_res.data)
        self.assertIn("endpoints", docs_data)

        dash_res = self.client.get('/')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"Open SERP & Lead-Gen", dash_res.data)
        self.assertIn(b"Local Search Inference Studio", dash_res.data)

if __name__ == "__main__":
    unittest.main()
