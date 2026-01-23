import unittest
from graph_db import GraphDB

class TestGraphDB(unittest.TestCase):
    def setUp(self):
        self.graph_db = GraphDB()

    def test_add_query(self):
        self.graph_db.add_query('q1', 'SELECT * FROM table')
        self.assertIn('q1', self.graph_db.get_graph().nodes)

    def test_add_relation(self):
        self.graph_db.add_query('q1', 'SELECT * FROM table')
        self.graph_db.add_query('q2', 'SELECT * FROM table WHERE condition')
        self.graph_db.add_relation('q1', 'q2')
        self.assertIn('q2', self.graph_db.get_graph()['q1'])

    def test_display_graph(self):
        self.graph_db.add_query('q1', 'SELECT * FROM table')
        self.graph_db.add_query('q2', 'SELECT * FROM table WHERE condition')
        self.graph_db.add_relation('q1', 'q2')
        expected_output = {'q1': ['q2'], 'q2': []}
        self.assertEqual(self.graph_db.display_graph(), expected_output)

if __name__ == '__main__':
    unittest.main()