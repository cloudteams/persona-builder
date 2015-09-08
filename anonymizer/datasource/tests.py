from anonymizer.datasource.managers import Property, \
    UserManagerException, ProviderNotFound, ProviderMethodNotFound, UserManager
from anonymizer.datasource.connections import ConnectionManager, ConnectionNotFound
from anonymizer.datasource.util import Configuration

__author__ = 'dipap'

from django.test import TestCase


class ConnectionTests(TestCase):

    def setUp(self):
        config = Configuration('test-data/config/sqlite3_config.json')
        self.sqlite3 = ConnectionManager(config.get_connection_info()).get('my_site_db')

        config = Configuration('test-data/config/mysql_config.json')
        self.mysql = ConnectionManager(config.get_connection_info()).get('my_other_db')

        super(ConnectionTests, self).setUp()

    def test_tables(self):
        # sqlite also reports the system special table
        self.assertEqual(len(self.sqlite3.tables()), 3)
        self.assertEqual(len(self.mysql.tables()), 3)

    def test_table_primary_key(self):
        self.assertEqual(self.sqlite3.primary_key_of('users'), 'users.id@my_site_db')
        self.assertEqual(self.mysql.primary_key_of('users'), 'users.id@my_other_db')

    def test_table_properties(self):
        # sqlite falsely reports the id, too
        self.assertEqual(len(self.sqlite3.get_data_properties('users')), 6)
        self.assertEqual(len(self.mysql.get_data_properties('users')), 5)

        # make sure first element is column name
        self.assertTrue(type(self.sqlite3.get_data_properties('users')[0][0]) == unicode)
        self.assertTrue(type(self.mysql.get_data_properties('users')[0][0]) == unicode)

        # also check the properties from other tables pointing to Users as well
        self.assertEqual(len(self.sqlite3.get_data_properties('users', from_related=True)), 9)
        self.assertEqual(len(self.mysql.get_data_properties('users', from_related=True)), 6)

    def test_related_tables(self):
        self.assertIn('Running', self.sqlite3.get_related_tables('users'))
        self.assertNotIn('Running_wrong', self.sqlite3.get_related_tables('users'))

        self.assertIn('running', self.mysql.get_related_tables('users'))
        self.assertNotIn('running_wrong', self.mysql.get_related_tables('users'))


class ConnectionManagerTests(TestCase):

    def test_exception_connection_not_found(self):
        config = Configuration('test-data/config/sqlite3_config.json')
        cm = ConnectionManager(config.get_connection_info())

        with self.assertRaises(ConnectionNotFound):
            cm.get('wrong_db')


class PropertyTests(TestCase):

    def setUp(self):
        self.um = UserManager('test-data/config/sqlite3_config.json')
        super(PropertyTests, self).setUp()

    def test_load_existing_provider(self):
        Property(self.um, '^Person.first_name', None)

    def test_exception_on_wrong_provider(self):
        with self.assertRaises(ProviderNotFound):
            Property(self.um, '^Person_wrong.first_name', None)

    def test_exception_on_wrong_provider_method(self):
        with self.assertRaises(ProviderMethodNotFound):
            Property(self.um, '^Person.first_name_wrong', None)

    def test_dynamic_type_with_helper(self):
        p = Property(self.um, '^Ranges.from_float_value(10..20|20..30|30..40, 35)', None, tp='###')
        self.assertEqual(p.tp, 'Scalar(10..20,20..30,30..40)')

    def test_exception_on_missing_type_helper(self):
        with self.assertRaises(ProviderMethodNotFound):
            Property(self.um, '^Person.first_name', None, tp='###')

    def test_matches(self):
        self.assertTrue(Property.matches(5, '=5'))
        self.assertFalse(Property.matches(6, '=5'))

        self.assertFalse(Property.matches(6, '!=5'))
        self.assertTrue(Property.matches(5, '!=5'))

        self.assertTrue(Property.matches(4, '<5'))
        self.assertFalse(Property.matches(5, '<5'))

        self.assertTrue(Property.matches(6, '>5'))
        self.assertFalse(Property.matches(5, '>5'))

        self.assertTrue(Property.matches(4, '<=5'))
        self.assertTrue(Property.matches(5, '<=5'))
        self.assertFalse(Property.matches(6, '<=5'))

        self.assertTrue(Property.matches(6, '>=5'))
        self.assertTrue(Property.matches(5, '>=5'))
        self.assertFalse(Property.matches(4, '>=5'))

class UserManagerTests(TestCase):

    def setUp(self):
        self.um = UserManager('test-data/config/sqlite3_config.json')
        super(UserManagerTests, self).setUp()

    def test_user_exists(self):
        self.assertIsNotNone(self.um.get(100))

    def test_user_not_exists(self):
        with self.assertRaises(UserManagerException):
            self.um.get(101)

    def test_no_filter(self):
        res = self.um.all()
        self.assertEqual(len(res), 100)

    def test_single_filter(self):
        res = self.um.filter('age=37')
        self.assertEqual(len(res), 2)

    def test_multiple_filter(self):
        res = self.um.filter(['gender="Male"', 'age<35'])
        self.assertEqual(len(res), 18)

    def test_custom_filter(self):
        res = self.um.filter('age=37 OR gender="Male"')
        self.assertEqual(len(res), 51)

    def test_aggregate_filter(self):
        res = self.um.filter(['age=37', 'run_duration_avg<13'])
        self.assertEqual(len(res), 1)

