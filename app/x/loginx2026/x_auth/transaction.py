"""
Client Transaction ID — توليد x-client-transaction-id
يستخدم مكتبة xclienttransaction المُحدّثة
"""
import re

import bs4
from x_client_transaction import ClientTransaction as _LibClientTransaction
from x_client_transaction.utils import get_ondemand_file_url


async def _handle_x_migration(session, headers):
    """جلب صفحة x.com مع معالجة إعادة التوجيه من twitter.com"""
    migration_redirection_regex = re.compile(
        r"""(http(?:s)?://(?:www\.)?(twitter|x){1}\.com(/x)?/migrate([/?])?tok=[a-zA-Z0-9%\-_]+)+""", re.VERBOSE)
    response = await session.request(method="GET", url="https://x.com", headers=headers)
    home_page = bs4.BeautifulSoup(response.content, 'html.parser')
    migration_url = home_page.select_one("meta[http-equiv='refresh']")
    migration_redirection_url = re.search(migration_redirection_regex, str(
        migration_url)) or re.search(migration_redirection_regex, str(response.content))
    if migration_redirection_url:
        response = await session.request(method="GET", url=migration_redirection_url.group(0), headers=headers)
        home_page = bs4.BeautifulSoup(response.content, 'html.parser')
    migration_form = home_page.select_one("form[name='f']") or home_page.select_one("form[action='https://x.com/x/migrate']")
    if migration_form:
        url = migration_form.attrs.get("action", "https://x.com/x/migrate") + "/?mx=2"
        method = migration_form.attrs.get("method", "POST")
        request_payload = {input_field.get("name"): input_field.get("value") for input_field in migration_form.select("input")}
        response = await session.request(method=method, url=url, data=request_payload, headers=headers)
        home_page = bs4.BeautifulSoup(response.content, 'html.parser')
    return home_page


class ClientTransaction:
    """غلاف حول مكتبة xclienttransaction — نفس الواجهة القديمة"""

    def __init__(self):
        self._ct = None

    async def init(self, session, headers):
        # 1. جلب صفحة x.com الرئيسية
        home_page_response = await _handle_x_migration(session, headers)

        # 2. استخراج رابط ملف ondemand.s من المكتبة
        ondemand_file_url = get_ondemand_file_url(response=home_page_response)
        if not ondemand_file_url:
            raise Exception("Could not extract ondemand JS URL from homepage")
        print(f'    ondemand URL: {ondemand_file_url}')

        # 3. جلب ملف ondemand JS
        ondemand_resp = await session.request(method="GET", url=ondemand_file_url, headers=headers)
        ondemand_text = ondemand_resp.text

        # 4. تهيئة المكتبة
        self._ct = _LibClientTransaction(
            home_page_response=home_page_response,
            ondemand_file_response=ondemand_text,
        )
        print(f'    ClientTransaction initialized successfully')

    def generate_transaction_id(self, method, path):
        if self._ct is None:
            raise Exception("ClientTransaction not initialized. Call init() first.")
        return self._ct.generate_transaction_id(method=method, path=path)
