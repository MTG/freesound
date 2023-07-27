#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#


from django.test import TestCase

from utils.text import clean_html, is_shouting, text_may_be_spam, remove_control_chars


class TextUtilTest(TestCase):
    """Tests for general text modification/analysis methods"""

    def test_is_shouting(self):
        (is_shouting(''))
        self.assertTrue(is_shouting('HELLO THIS IS SHOUTING!!!'))
        self.assertFalse(is_shouting('This is a phrase WITH SOME emphasis!!'))
        self.assertFalse(is_shouting('This is a regular phrase.'))

    def test_text_may_be_spam(self):
        self.assertFalse(text_may_be_spam(''))
        self.assertFalse(text_may_be_spam('  '))
        self.assertFalse(text_may_be_spam('this is the content of a blog post'))
        self.assertTrue(text_may_be_spam('this post contains an http:// link'))
        self.assertTrue(text_may_be_spam('this post contains an https:// link'))
        self.assertTrue(text_may_be_spam('this post contains non-basic ascii characters :'))
        self.assertTrue(text_may_be_spam('this post contains non-basic ascii characters \xc3'))
        self.assertFalse(text_may_be_spam('this post contains few numbers 1245'))
        self.assertTrue(text_may_be_spam('this post contains more numbers 1234567'))
        self.assertTrue(text_may_be_spam('this post contains even more numbers 123456789'))
        self.assertTrue(text_may_be_spam('this post contains an@email.com'))
        self.assertTrue(text_may_be_spam('this post contains short.url'))
        self.assertTrue(text_may_be_spam('BLaCk MaGiC SpEcIaLiSt babaji'))
        self.assertTrue(text_may_be_spam('love marriage problem solution'))
        self.assertTrue(text_may_be_spam('fbdad8fbdad8fbdad8'))
        self.assertTrue(text_may_be_spam('fbdad8'))

    def test_remove_control_chars(self):
        text = "some \xf0\x9f\x98\x80 emoji"
        self.assertEqual(remove_control_chars(text), "some \xf0\x9f\x98\x80 emoji")
        unicodeemoji = "hello \U0001f600"
        self.assertEqual(remove_control_chars(unicodeemoji), "hello \U0001f600")
        text = "normal text"
        self.assertEqual(remove_control_chars(text), "normal text")
        text = "text with \n newline"
        self.assertEqual(remove_control_chars(text), "text with \n newline")
        text = "text with control\x08char"
        self.assertEqual(remove_control_chars(text), "text with controlchar")


class CleanHtmlTest(TestCase):

    def test_clean_html(self):
        # Test if the text input contains allowed html tags
        # The only supported tags are : a, img, strong, b, em, li, u, p, br, blockquote and code
        ret = clean_html('a b c d')
        self.assertEqual('a b c d', ret)

        # Also make sure links contains rel="nofollow"
        ret = clean_html('<a href="http://www.google.com" rel="squeek">google</a>')
        self.assertEqual('<a href="http://www.google.com" rel="nofollow">google</a>', ret)

        ret = clean_html('<a href="http://www.google.com">google</a>')
        self.assertEqual('<a href="http://www.google.com" rel="nofollow">google</a>', ret)

        ret = clean_html('<h1>this should return the <strong>substring</strong> just <b>fine</b></h1>')
        self.assertEqual('this should return the <strong>substring</strong> just <b>fine</b>', ret)

        ret = clean_html('<table><tr><td>amazing</td><td>grace</td></tr></table>')
        self.assertEqual('amazinggrace', ret)

        ret = clean_html('<a href="javascript:void(0)">click me</a>')
        self.assertEqual('click me', ret)

        ret = clean_html('<p class="hello">click me</p>')
        self.assertEqual('<p>click me</p>', ret)

        ret = clean_html('<a></a>')
        self.assertEqual('', ret)

        ret = clean_html('<a>hello</a>')
        self.assertEqual('hello', ret)

        ret = clean_html('<p class="hello" id="1">a<br/>b<br/></a>')
        self.assertEqual('<p>a<br>b<br></p>', ret)

        ret = clean_html('<p></p>')
        self.assertEqual('<p></p>', ret)

        ret = clean_html('<A REL="nofollow" hREF="http://www.google.com"><strong>http://www.google.com</strong></a>')
        self.assertEqual('<a rel="nofollow" href="http://www.google.com"><strong>http://www.google.com</strong></a>', ret)

        ret = clean_html('<a rel="nofollow" href="http://www.google.com"><strong>http://www.google.com</strong></a>')
        self.assertEqual('<a rel="nofollow" href="http://www.google.com"><strong>http://www.google.com</strong></a>', ret)

        ret = clean_html('http://www.google.com <a href="">http://www.google.com</a>')
        self.assertEqual('<a href="http://www.google.com" rel="nofollow">http://www.google.com</a> <a href="http://www.google.com" rel="nofollow">http://www.google.com</a>', ret)

        ret = clean_html('<ul><p id=5><a href="123">123</a>hello<strong class=156>there http://www.google.com</strong></p></ul>')
        self.assertEqual('<ul><p>123hello<strong>there <a href="http://www.google.com" rel="nofollow">http://www.google.com</a></strong></p></ul>', ret)

        ret = clean_html('abc http://www.google.com abc')
        self.assertEqual('abc <a href="http://www.google.com" rel="nofollow">http://www.google.com</a> abc', ret)

        # The links inside <> are encoded by &lt; and &gt;
        ret = clean_html('abc <http://www.google.com> abc')
        self.assertEqual('abc &lt; <a href="http://www.google.com" rel="nofollow">http://www.google.com</a> &gt; abc', ret)

        ret = clean_html('GALORE: https://freesound.iua.upf.edu/samplesViewSingle.php?id=22092\\nFreesound Moderator')
        self.assertEqual('GALORE: <a href="https://freesound.iua.upf.edu/samplesViewSingle.php?id=22092" rel="nofollow">https://freesound.iua.upf.edu/samplesViewSingle.php?id=22092</a>\\nFreesound Moderator', ret)

        # Allow custom placeholders
        ret = clean_html('<a href="${sound_id}">my sound id</a>')
        self.assertEqual('<a href="${sound_id}" rel="nofollow">my sound id</a>', ret)

        ret = clean_html('<a href="${sound_url}">my sound url</a>')
        self.assertEqual('<a href="${sound_url}" rel="nofollow">my sound url</a>', ret)

        ret = clean_html('<img src="https://freesound.org/media/images/logo.png">')
        self.assertEqual('<img src="https://freesound.org/media/images/logo.png">', ret)

        ret = clean_html('<ul><li>Some list</li></ul>')
        self.assertEqual('<ul><li>Some list</li></ul>', ret)
