"""
Client Transaction ID — توليد x-client-transaction-id
"""
import re
import math
import time
import random
import base64
import hashlib
from functools import reduce

import bs4

from .crypto import float_to_hex, is_odd, base64_encode, n_digit_hex


# ============ Cubic Bezier ============
class Cubic:
    def __init__(self, curves):
        self.curves = curves

    def get_value(self, t):
        start_gradient = end_gradient = start = mid = 0.0
        end = 1.0
        if t <= 0.0:
            if self.curves[0] > 0.0:
                start_gradient = self.curves[1] / self.curves[0]
            elif self.curves[1] == 0.0 and self.curves[2] > 0.0:
                start_gradient = self.curves[3] / self.curves[2]
            return start_gradient * t
        if t >= 1.0:
            if self.curves[2] < 1.0:
                end_gradient = (self.curves[3] - 1.0) / (self.curves[2] - 1.0)
            elif self.curves[2] == 1.0 and self.curves[0] < 1.0:
                end_gradient = (self.curves[1] - 1.0) / (self.curves[0] - 1.0)
            return 1.0 + end_gradient * (t - 1.0)
        while start < end:
            mid = (start + end) / 2
            x_est = self.calculate(self.curves[0], self.curves[2], mid)
            if abs(t - x_est) < 0.00001:
                return self.calculate(self.curves[1], self.curves[3], mid)
            if x_est < t:
                start = mid
            else:
                end = mid
        return self.calculate(self.curves[1], self.curves[3], mid)

    @staticmethod
    def calculate(a, b, m):
        return 3.0 * a * (1 - m) * (1 - m) * m + 3.0 * b * (1 - m) * m * m + m * m * m


# ============ Interpolate ============
def interpolate(from_list, to_list, f):
    out = []
    for i in range(len(from_list)):
        fv, tv = from_list[i], to_list[i]
        if isinstance(fv, (int, float)) and isinstance(tv, (int, float)):
            out.append(fv * (1 - f) + tv * f)
        elif isinstance(fv, bool) and isinstance(tv, bool):
            out.append(fv if f < 0.5 else tv)
        else:
            out.append(fv)
    return out


# ============ Rotation ============
def convert_rotation_to_matrix(rotation):
    rad = math.radians(rotation)
    return [math.cos(rad), -math.sin(rad), math.sin(rad), math.cos(rad)]


# ============ Handle X Migration ============
ON_DEMAND_FILE_REGEX = re.compile(
    r"""['|\"]{1}ondemand\.s['|\"]{1}:\s*['|\"]{1}([\w]*)['|\"]{1}""", flags=(re.VERBOSE | re.MULTILINE))
INDICES_REGEX = re.compile(
    r"""(\(\w{1}\[(\d{1,2})\],\s*16\))+""", flags=(re.VERBOSE | re.MULTILINE))


async def handle_x_migration(session, headers):
    migration_redirection_regex = re.compile(
        r"""(http(?:s)?://(?:www\.)?(twitter|x){1}\.com(/x)?/migrate([/?])?tok=[a-zA-Z0-9%\-_]+)+""", re.VERBOSE)
    response = await session.request(method="GET", url="https://x.com", headers=headers)
    home_page = bs4.BeautifulSoup(response.content, 'lxml')
    migration_url = home_page.select_one("meta[http-equiv='refresh']")
    migration_redirection_url = re.search(migration_redirection_regex, str(
        migration_url)) or re.search(migration_redirection_regex, str(response.content))
    if migration_redirection_url:
        response = await session.request(method="GET", url=migration_redirection_url.group(0), headers=headers)
        home_page = bs4.BeautifulSoup(response.content, 'lxml')
    migration_form = home_page.select_one("form[name='f']") or home_page.select_one("form[action='https://x.com/x/migrate']")
    if migration_form:
        url = migration_form.attrs.get("action", "https://x.com/x/migrate") + "/?mx=2"
        method = migration_form.attrs.get("method", "POST")
        request_payload = {input_field.get("name"): input_field.get("value") for input_field in migration_form.select("input")}
        response = await session.request(method=method, url=url, data=request_payload, headers=headers)
        home_page = bs4.BeautifulSoup(response.content, 'lxml')
    return home_page


# ============ ClientTransaction ============
class ClientTransaction:
    ADDITIONAL_RANDOM_NUMBER = 3
    DEFAULT_KEYWORD = "obfiowerehiring"

    def __init__(self):
        self.home_page_response = None
        self.DEFAULT_ROW_INDEX = None
        self.DEFAULT_KEY_BYTES_INDICES = None
        self.key = None
        self.key_bytes = None
        self.animation_key = None

    async def init(self, session, headers):
        home_page_response = await handle_x_migration(session, headers)
        self.home_page_response = self._validate(home_page_response)
        self.DEFAULT_ROW_INDEX, self.DEFAULT_KEY_BYTES_INDICES = await self._get_indices(
            self.home_page_response, session, headers)
        self.key = self._get_key(self.home_page_response)
        self.key_bytes = self._get_key_bytes(self.key)
        self.animation_key = self._get_animation_key(self.key_bytes, self.home_page_response)

    async def _get_indices(self, home_page_response, session, headers):
        key_byte_indices = []
        response = self._validate(home_page_response)
        on_demand_file = ON_DEMAND_FILE_REGEX.search(str(response))
        if on_demand_file:
            on_demand_file_url = f"https://abs.twimg.com/responsive-web/client-web/ondemand.s.{on_demand_file.group(1)}a.js"
            on_demand_file_response = await session.request(method="GET", url=on_demand_file_url, headers=headers)
            key_byte_indices_match = INDICES_REGEX.finditer(str(on_demand_file_response.text))
            for item in key_byte_indices_match:
                key_byte_indices.append(item.group(2))
        if not key_byte_indices:
            raise Exception("Couldn't get KEY_BYTE indices")
        key_byte_indices = list(map(int, key_byte_indices))
        return key_byte_indices[0], key_byte_indices[1:]

    def _validate(self, response):
        if not isinstance(response, bs4.BeautifulSoup):
            raise Exception("invalid response")
        return response

    def _get_key(self, response):
        element = response.select_one("[name='twitter-site-verification']")
        if not element:
            raise Exception("Couldn't get key from the page source")
        return element.get("content")

    def _get_key_bytes(self, key):
        return list(base64.b64decode(bytes(key, 'utf-8')))

    def _get_frames(self, response):
        return response.select("[id^='loading-x-anim']")

    def _get_2d_array(self, key_bytes, response, frames=None):
        if not frames:
            frames = self._get_frames(response)
        return [[int(x) for x in re.sub(r"[^\d]+", " ", item).strip().split()] for item in list(list(frames[key_bytes[5] % 4].children)[0].children)[1].get("d")[9:].split("C")]

    def _solve(self, value, min_val, max_val, rounding):
        result = value * (max_val - min_val) / 255 + min_val
        return math.floor(result) if rounding else round(result, 2)

    def _animate(self, frames, target_time):
        from_color = [float(item) for item in [*frames[:3], 1]]
        to_color = [float(item) for item in [*frames[3:6], 1]]
        from_rotation = [0.0]
        to_rotation = [self._solve(float(frames[6]), 60.0, 360.0, True)]
        frames = frames[7:]
        curves = [self._solve(float(item), is_odd(counter), 1.0, False)
                  for counter, item in enumerate(frames)]
        cubic = Cubic(curves)
        val = cubic.get_value(target_time)
        color = interpolate(from_color, to_color, val)
        color = [value if value > 0 else 0 for value in color]
        rotation = interpolate(from_rotation, to_rotation, val)
        matrix = convert_rotation_to_matrix(rotation[0])
        str_arr = [format(round(value), 'x') for value in color[:-1]]
        for value in matrix:
            rounded = round(value, 2)
            if rounded < 0:
                rounded = -rounded
            hex_value = float_to_hex(rounded)
            str_arr.append(f"0{hex_value}".lower() if hex_value.startswith(
                ".") else hex_value if hex_value else '0')
        str_arr.extend(["0", "0"])
        animation_key = re.sub(r"[.-]", "", "".join(str_arr))
        return animation_key

    def _get_animation_key(self, key_bytes, response):
        total_time = 4096
        row_index = key_bytes[self.DEFAULT_ROW_INDEX] % 16
        frame_time = reduce(lambda num1, num2: num1 * num2,
                            [key_bytes[index] % 16 for index in self.DEFAULT_KEY_BYTES_INDICES])
        arr = self._get_2d_array(key_bytes, response)
        frame_row = arr[row_index]
        target_time = float(frame_time) / total_time
        return self._animate(frame_row, target_time)

    def generate_transaction_id(self, method, path):
        time_now = math.floor((time.time() * 1000 - 1682924400 * 1000) / 1000)
        time_now_bytes = [(time_now >> (i * 8)) & 0xFF for i in range(4)]
        key_bytes = self._get_key_bytes(self.key)
        hash_val = hashlib.sha256(
            f"{method}!{path}!{time_now}{self.DEFAULT_KEYWORD}{self.animation_key}".encode()).digest()
        hash_bytes = list(hash_val)
        random_num = random.randint(0, 255)
        bytes_arr = [*key_bytes, *time_now_bytes, *hash_bytes[:16], self.ADDITIONAL_RANDOM_NUMBER]
        out = bytearray([random_num, *[item ^ random_num for item in bytes_arr]])
        return base64_encode(out).strip("=")
