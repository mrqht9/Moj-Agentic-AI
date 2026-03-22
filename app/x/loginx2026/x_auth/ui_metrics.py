"""
حل JS Instrumentation باستخدام محرك V8
"""
import re
import STPyV8


# ============ Mock DOM ============
class MockElement:
    def __init__(self, tag_name, document):
        self.tagName = tag_name
        self.document = document
        self.parentNode = None

    def appendChild(self, child):
        child.parentNode = self

    def remove(self):
        self.document.element_seq.remove(self)

    def removeChild(self, child):
        child.remove()

    @property
    def lastElementChild(self):
        if self.children:
            return self.children[-1]

    def setAttribute(self, name, value):
        pass

    @property
    def children(self):
        return self.document._filter_elements(lambda x: x.parentNode == self)


class MockDocument:
    def __init__(self):
        self.element_seq = []
        self.body = self.createElement('body')

    def createElement(self, tag_name):
        element = MockElement(tag_name, self)
        self.element_seq.append(element)
        return element

    def _filter_elements(self, function):
        return list(filter(function, self.element_seq))

    def getElementsByTagName(self, tag_name):
        return self._filter_elements(lambda x: x.tagName == tag_name)


# ============ Solve ============
FUNCTION_PATTERN = re.compile(r'function [a-zA-Z]+\(\) ({.+})')


def solve_ui_metrics(ui_metrics_js):
    match = FUNCTION_PATTERN.search(ui_metrics_js)
    if not match:
        raise ValueError('No function pattern found in ui_metrics input')
    inner_function = match.group(1)

    with STPyV8.JSContext() as ctxt:
        ctxt.locals.document = MockDocument()
        js = '''
        (() => {
            try {
                return JSON.stringify((() => %s)());
            } catch (e) {
                throw new Error();
            }
        })()
        ''' % inner_function
        return ctxt.eval(js)
