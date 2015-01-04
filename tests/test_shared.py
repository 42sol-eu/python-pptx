# encoding: utf-8

"""
Test suite for the docx.shared module
"""

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import pytest

from pptx.shared import ElementProxy, ParentedElementProxy

from .unitutil.cxml import element


class DescribeElementProxy(object):

    def it_raises_on_assign_to_undefined_attr(self):
        element_proxy = ElementProxy(None)
        with pytest.raises(AttributeError):
            element_proxy.foobar = 42

    def it_knows_when_its_equal_to_another_proxy_object(self, eq_fixture):
        proxy, proxy_2, proxy_3, not_a_proxy = eq_fixture

        assert (proxy == proxy_2) is True
        assert (proxy == proxy_3) is False
        assert (proxy == not_a_proxy) is False

        assert (proxy != proxy_2) is False
        assert (proxy != proxy_3) is True
        assert (proxy != not_a_proxy) is True

    def it_knows_its_element(self, element_fixture):
        proxy, element = element_fixture
        assert proxy.element is element

    # fixture --------------------------------------------------------

    @pytest.fixture
    def element_fixture(self):
        p = element('w:p')
        proxy = ElementProxy(p)
        return proxy, p

    @pytest.fixture
    def eq_fixture(self):
        p, q = element('w:p'), element('w:p')
        proxy = ElementProxy(p)
        proxy_2 = ElementProxy(p)
        proxy_3 = ElementProxy(q)
        not_a_proxy = 'Foobar'
        return proxy, proxy_2, proxy_3, not_a_proxy


class DescribeParentedElementProxy(object):

    def it_knows_its_parent(self, parent_fixture):
        proxy, parent = parent_fixture
        assert proxy.parent is parent

    # fixture --------------------------------------------------------

    @pytest.fixture
    def parent_fixture(self):
        parent = 42
        proxy = ParentedElementProxy(element('w:p'), parent)
        return proxy, parent
