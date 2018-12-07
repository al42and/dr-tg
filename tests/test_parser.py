import os
import unittest
import codecs
from unittest.mock import patch, Mock

import settings
from parser import Parser


class ParserTestCase(unittest.TestCase):
    @patch('parser.settings.DATASET', settings.DATASET_TEST)
    def setUp(self):
        self.parser = Parser()

    def tearDown(self):
        """Очищаем таблицы после прохождения каждого теста"""
        self.parser.table_bot.delete()
        self.parser.table_tip.delete()
        self.parser.table_code.delete()
        self.parser.table_sector.delete()

    def set_html(self, filename):
        filepath = os.path.join(os.path.dirname(__file__), filename)
        with codecs.open(filepath, encoding='cp1251') as f:
            html = f.read()
            html_bytes = bytes(html, encoding='cp1251')
            self.parser.g.setup_document(html_bytes)

    def test_parse_level_multiple(self):
        """Несколько секторов"""
        self.set_html('pages/2sector.html')
        self.parser.parse()

        self.assertEqual(self.parser.table_sector.count(), 2)

        sector_1 = self.parser.table_sector.find_one()
        self.assertEqual(sector_1['name'], 'бонусные коды')
        code = self.parser.table_code.find_one(metka=1, sector_id=sector_1['id'])
        self.assertEqual(code['ko'], 'N')

    def test_parse_level_one(self):
        """Один сектор, многие коды взяты"""
        self.set_html('pages/tip_1.html')
        self.parser.parse()

        self.assertEqual(self.parser.table_sector.count(), 1)
        self.assertEqual(self.parser.table_code.count(), 14)

        code_1 = self.parser.table_code.find_one(metka=1)
        self.assertEqual(code_1['ko'], '3')
        self.assertEqual(code_1['taken'], True)

        code_2 = self.parser.table_code.find_one(metka=2)
        self.assertEqual(code_2['ko'], '2')
        self.assertEqual(code_2['taken'], False)

    def test_new_metki(self):
        self.set_html('pages/code_1.html')
        result = self.parser.parse()
        self.assertEqual(len(result['new_metki']), 0)
        self.set_html('pages/code_2.html')
        result = self.parser.parse()
        self.assertEqual(len(result['new_metki']), 1)
        new_codes = [(m['sector_name'], m['metka']) for m in result['new_metki']]
        self.assertIn(('основные коды', 8), new_codes)

    def test_new_metki_multiple(self):
        self.set_html('pages/code_1.html')
        result = self.parser.parse()
        self.assertEqual(len(result['new_metki']), 0)
        self.set_html('pages/code_3.html')
        result = self.parser.parse()
        self.assertEqual(len(result['new_metki']), 2)
        new_codes = [(m['sector_name'], m['metka']) for m in result['new_metki']]
        self.assertIn(('основные коды', 8), new_codes)
        self.assertIn(('основные коды', 11), new_codes)

    def test_new_metki_no(self):
        self.set_html('pages/code_1.html')
        result = self.parser.parse()
        self.assertEqual(len(result['new_metki']), 0)
        self.set_html('pages/code_1.html')
        result = self.parser.parse()
        self.assertEqual(len(result['new_metki']), 0)

    def test_new_metki_two_sectors(self):
        self.set_html('pages/sectors_1.html')
        result = self.parser.parse()
        self.assertEqual(len(result['new_metki']), 0)
        self.set_html('pages/sectors_2.html')
        result = self.parser.parse()
        self.assertEqual(len(result['new_metki']), 1)
        new_codes = [(m['sector_name'], m['metka']) for m in result['new_metki']]
        self.assertIn(('забор: основные коды', 3), new_codes)

    def test_parse_tip(self):
        self.set_html('pages/tip_1.html')
        result = self.parser.parse()
        self.assertEqual(len(result['tip_list']), 0)
        self.assertEqual(self.parser.table_tip.count(), 0)  # Подсказок в базе не должно быть

        tip_text = 'Ответ на спойлер: пустырь'
        self.set_html('pages/tip_2.html')
        result = self.parser.parse()
        self.assertEqual(result['tip_list'][0]['text'], tip_text)

        self.assertEqual(self.parser.table_tip.count(), 1)  # Должна появится первая подсказка
        tip = self.parser.table_tip.find_one()
        self.assertEqual(tip['text'], tip_text)

    def test_parse_spoiler(self):
        self.set_html('pages/spoiler_1.html')
        result = self.parser.parse()
        self.assertEqual(result['new_spoiler'], False)

        self.set_html('pages/spoiler_1.html')
        result = self.parser.parse()
        self.assertEqual(result['new_spoiler'], False)

        self.set_html('pages/spoiler_2.html')
        result = self.parser.parse()
        self.assertEqual(result['new_spoiler'], True)

    def test_parse_message(self):
        self.set_html('pages/code_1.html')
        result = self.parser.parse()
        self.assertEqual(result['message'], '')

        self.set_html('pages/sysmsg_no_bold.html')
        result = self.parser.parse()
        self.assertEqual(result['message'],
                         'Вы нашли все основные коды. Вы можете продолжать искать бонусные коды или перейти на следующий уровень.')

        self.set_html('pages/sysmsg_bold.html')
        result = self.parser.parse()
        self.assertEqual(result['message'], 'Код принят.')
